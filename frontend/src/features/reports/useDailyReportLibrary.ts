import { useCallback, useEffect, useMemo, useState } from 'react';
import * as FileSystem from 'expo-file-system/legacy';
import { Share } from 'react-native';

import { getDailyReport, getDailyReportPdfUrl } from '@/services/api';

import {
  buildReportFileName,
  createReportRecord,
  groupReportRecords,
  isMinimumViableReport,
  migrateReportRecords,
  type DailyReportRecord,
} from './reportLibraryModel';

const STORAGE_KEY = 'market-intelligence-daily-report-records-v1';
const GENERATION_STAGES = [
  'Collecting market data…',
  'Building market overview…',
  'Preparing charts…',
  'Writing market remarks…',
  'Finalizing report…',
];

export function useDailyReportLibrary() {
  const [records, setRecords] = useState<DailyReportRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [workingId, setWorkingId] = useState<string | null>(null);
  const [generationMessage, setGenerationMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    loadRecords().then(async (stored) => {
      const reconciled = await reconcileDownloadedRecords(stored);
      if (!mounted) {
        return;
      }
      setRecords(reconciled);
      setLoading(false);
      if (reconciled.length !== stored.length || JSON.stringify(reconciled) !== JSON.stringify(stored)) {
        saveRecords(reconciled);
      }
    }).catch(() => {
      if (mounted) {
        setRecords([]);
        setLoading(false);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  const grouped = useMemo(() => groupReportRecords(records), [records]);
  const todayRecordCount = records.filter((record) => record.metadata.marketDate === new Date().toISOString().slice(0, 10)).length;

  const updateRecord = useCallback((id: string, patch: Partial<DailyReportRecord>) => {
    setRecords((current) => {
      const next = current.map((record) => record.id === id ? { ...record, ...patch } : record);
      saveRecords(next);
      return next;
    });
  }, []);

  const generateTodayReport = useCallback(async () => {
    if (workingId) {
      return null;
    }
    setWorkingId('generate');
    setError(null);
    try {
      for (const stage of GENERATION_STAGES) {
        setGenerationMessage(stage);
        await delay(80);
      }
      const report = await getDailyReport();
      if (!isMinimumViableReport(report)) {
        throw new Error('minimum_report_unavailable');
      }
      const record = createReportRecord({
        existingRecords: records,
        pdfUrl: getDailyReportPdfUrl(),
        report,
      });
      const next = [record, ...records];
      setRecords(next);
      saveRecords(next);
      setGenerationMessage('Report ready to download.');
      return record;
    } catch {
      setError('Unable to generate the report.');
      setGenerationMessage(null);
      return null;
    } finally {
      setWorkingId(null);
    }
  }, [records, workingId]);

  const downloadReport = useCallback(async (record: DailyReportRecord) => {
    if (workingId) {
      return null;
    }
    setWorkingId(record.id);
    updateRecord(record.id, { status: 'downloading' });
    try {
      const downloaded = await downloadPdfForRecord(record);
      updateRecord(record.id, downloaded);
      return { ...record, ...downloaded } as DailyReportRecord;
    } catch {
      updateRecord(record.id, { errorCode: 'download_failed', status: 'download_failed' });
      return null;
    } finally {
      setWorkingId(null);
    }
  }, [updateRecord, workingId]);

  const removeReport = useCallback(async (record: DailyReportRecord) => {
    if (workingId) {
      return false;
    }
    setWorkingId(record.id);
    setError(null);
    try {
      if (record.localPdfUri) {
        await deleteLocalPdf(record.localPdfUri);
      }
      setRecords((current) => {
        const next = current.filter((item) => item.id !== record.id);
        saveRecords(next);
        return next;
      });
      return true;
    } catch {
      setError('Unable to remove the downloaded report.');
      return false;
    } finally {
      setWorkingId(null);
    }
  }, [workingId]);

  const shareReport = useCallback(async (record: DailyReportRecord) => {
    let target = record;
    if (!target.localPdfUri) {
      const downloaded = await downloadReport(record);
      if (!downloaded) {
        return;
      }
      target = downloaded;
    }
    await Share.share({
      message: `Daily Market Report ${target.metadata.marketDate}`,
      title: `Daily Market Report ${target.metadata.marketDate}`,
      url: target.localPdfUri ?? undefined,
    });
  }, [downloadReport]);

  return {
    downloadReport,
    error,
    generateTodayReport,
    generationMessage,
    grouped,
    loading,
    records,
    removeReport,
    shareReport,
    todayRecordCount,
    workingId,
  };
}

async function loadRecords() {
  try {
    const raw = getWebStorage()?.getItem(STORAGE_KEY) ?? await readFileStorage();
    return migrateReportRecords(raw ? JSON.parse(raw) : []);
  } catch {
    return [];
  }
}

function saveRecords(records: DailyReportRecord[]) {
  const raw = JSON.stringify(records);
  try {
    getWebStorage()?.setItem(STORAGE_KEY, raw);
  } catch {
    // Native storage remains available.
  }
  writeFileStorage(raw).catch(() => {
    // Report history persistence is best-effort.
  });
}

async function reconcileDownloadedRecords(records: DailyReportRecord[]) {
  const reconciled: DailyReportRecord[] = [];
  for (const record of records) {
    if (record.status === 'downloaded' && record.localPdfUri) {
      const info = await FileSystem.getInfoAsync(record.localPdfUri);
      if (!info.exists) {
        reconciled.push({
          ...record,
          fileSizeBytes: null,
          localPdfUri: null,
          metadata: { ...record.metadata, downloadedAt: null },
          status: 'ready',
        });
        continue;
      }
    }
    reconciled.push(record);
  }
  return reconciled;
}

async function downloadPdfForRecord(record: DailyReportRecord): Promise<Partial<DailyReportRecord>> {
  const baseDirectory = FileSystem.documentDirectory ?? FileSystem.cacheDirectory;
  if (!baseDirectory) {
    throw new Error('file_storage_unavailable');
  }
  const directory = `${baseDirectory}reports/`;
  await FileSystem.makeDirectoryAsync(directory, { intermediates: true });
  const fileName = record.fileName ?? buildReportFileName(record.metadata.marketDate, record.metadata.version);
  const destination = `${directory}${fileName}`;
  const result = await FileSystem.downloadAsync(record.remotePdfUrl ?? getDailyReportPdfUrl(), destination);
  if (result.status !== 200) {
    throw new Error('pdf_http_error');
  }
  await validatePdfFile(result.uri);
  const info = await FileSystem.getInfoAsync(result.uri);
  return {
    errorCode: null,
    fileName,
    fileSizeBytes: info.exists && 'size' in info && typeof info.size === 'number' ? info.size : null,
    localPdfUri: result.uri,
    metadata: {
      ...record.metadata,
      downloadedAt: new Date().toISOString(),
    },
    status: 'downloaded',
  };
}

async function deleteLocalPdf(uri: string) {
  const info = await FileSystem.getInfoAsync(uri);
  if (info.exists) {
    await FileSystem.deleteAsync(uri, { idempotent: true });
  }
}

async function validatePdfFile(uri: string) {
  const info = await FileSystem.getInfoAsync(uri);
  if (!info.exists || ('size' in info && typeof info.size === 'number' && info.size < 100)) {
    throw new Error('pdf_empty');
  }
  const content = await FileSystem.readAsStringAsync(uri, {
    encoding: FileSystem.EncodingType.Base64,
  });
  if (!content.startsWith('JVBER')) {
    throw new Error('pdf_signature_invalid');
  }
}

async function readFileStorage() {
  const path = getStoragePath();
  if (!path) {
    return null;
  }
  const info = await FileSystem.getInfoAsync(path);
  if (!info.exists) {
    return null;
  }
  return FileSystem.readAsStringAsync(path);
}

async function writeFileStorage(raw: string) {
  const path = getStoragePath();
  if (!path || !FileSystem.documentDirectory) {
    return;
  }
  await FileSystem.makeDirectoryAsync(FileSystem.documentDirectory, { intermediates: true });
  await FileSystem.writeAsStringAsync(path, raw);
}

function getStoragePath() {
  return FileSystem.documentDirectory ? `${FileSystem.documentDirectory}${STORAGE_KEY}.json` : null;
}

function getWebStorage(): Storage | null {
  if (typeof globalThis === 'undefined' || !('localStorage' in globalThis)) {
    return null;
  }
  return globalThis.localStorage;
}

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
