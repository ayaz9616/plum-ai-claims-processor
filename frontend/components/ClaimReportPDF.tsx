import React from 'react';
import { Document, Page, Text, View, StyleSheet, Font } from '@react-pdf/renderer';
import type { ClaimProcessingResult, ClaimSubmission, TraceEvent } from '../app/types';

const styles = StyleSheet.create({
  page: {
    padding: 40,
    fontFamily: 'Helvetica',
    fontSize: 10,
    color: '#334155',
  },
  header: {
    marginBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#cbd5e1',
    paddingBottom: 10,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#0f172a',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 12,
    color: '#64748b',
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#0f172a',
    backgroundColor: '#f1f5f9',
    padding: 5,
    marginBottom: 10,
  },
  row: {
    flexDirection: 'row',
    marginBottom: 5,
  },
  label: {
    width: 150,
    fontWeight: 'bold',
    color: '#475569',
  },
  value: {
    flex: 1,
  },
  table: {
    display: 'flex',
    flexDirection: 'column',
    width: 'auto',
    borderStyle: 'solid',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRightWidth: 0,
    borderBottomWidth: 0,
  },
  tableRow: {
    flexDirection: 'row',
  },
  tableColHeader: {
    width: '20%',
    borderStyle: 'solid',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderLeftWidth: 0,
    borderTopWidth: 0,
    backgroundColor: '#f8fafc',
    padding: 5,
    fontWeight: 'bold',
  },
  tableCol: {
    width: '20%',
    borderStyle: 'solid',
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderLeftWidth: 0,
    borderTopWidth: 0,
    padding: 5,
  },
  tableCellHeader: {
    fontSize: 9,
    fontWeight: 'bold',
  },
  tableCell: {
    fontSize: 9,
  },
  warningBox: {
    backgroundColor: '#fef3c7',
    border: '1px solid #fde68a',
    padding: 10,
    marginBottom: 10,
    borderRadius: 4,
  },
  warningText: {
    color: '#92400e',
    fontWeight: 'bold',
  },
  footer: {
    position: 'absolute',
    bottom: 30,
    left: 40,
    right: 40,
    textAlign: 'center',
    color: '#94a3b8',
    fontSize: 8,
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
    paddingTop: 10,
  }
});

interface ClaimReportPDFProps {
  submission: ClaimSubmission;
  result: ClaimProcessingResult;
}

export function ClaimReportPDF({ submission, result }: ClaimReportPDFProps) {
  const docVerifyTrace = result.trace.find(t => t.step === "DOCUMENT_VERIFICATION");
  const policyTrace = result.trace.find(t => t.step === "POLICY_EVALUATION");
  const financeTrace = result.trace.find(t => t.step === "FINANCIAL_CALCULATION");
  const fraudTrace = result.trace.find(t => t.step === "FRAUD_ANALYSIS");

  const lineItems = financeTrace?.safe_output?.breakdown?.line_items || [];
  
  return (
    <Document>
      <Page size="A4" style={styles.page}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Plum Claims AI</Text>
          <Text style={styles.subtitle}>Claim Processing Report</Text>
          <Text style={styles.subtitle}>Date: {new Date().toLocaleString()}</Text>
          <Text style={styles.subtitle}>Claim ID: {result.claim_id}</Text>
        </View>

        {/* Claim Summary */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Claim Summary</Text>
          <View style={styles.row}><Text style={styles.label}>Member ID:</Text><Text style={styles.value}>{submission.member_id}</Text></View>
          <View style={styles.row}><Text style={styles.label}>Policy ID:</Text><Text style={styles.value}>{submission.policy_id}</Text></View>
          <View style={styles.row}><Text style={styles.label}>Claim Category:</Text><Text style={styles.value}>{submission.claim_category}</Text></View>
          <View style={styles.row}><Text style={styles.label}>Treatment Date:</Text><Text style={styles.value}>{submission.treatment_date}</Text></View>
          <View style={styles.row}><Text style={styles.label}>Claimed Amount:</Text><Text style={styles.value}>₹{submission.claimed_amount}</Text></View>
          <View style={styles.row}><Text style={styles.label}>Approved Amount:</Text><Text style={styles.value}>{result.approved_amount != null ? `₹${result.approved_amount}` : 'N/A'}</Text></View>
          <View style={styles.row}><Text style={styles.label}>Final Decision:</Text><Text style={styles.value}>{result.decision || 'N/A'}</Text></View>
          <View style={styles.row}><Text style={styles.label}>Processing Status:</Text><Text style={styles.value}>{result.processing_status}</Text></View>
        </View>

        {/* Decision & Confidence */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Decision &amp; Confidence</Text>
          <View style={styles.row}><Text style={styles.label}>Decision:</Text><Text style={styles.value}>{result.decision || 'N/A'}</Text></View>
          <View style={styles.row}><Text style={styles.label}>Confidence Score:</Text><Text style={styles.value}>{result.confidence_score != null ? `${(result.confidence_score * 100).toFixed(0)}%` : 'N/A'}</Text></View>
          <View style={styles.row}><Text style={styles.label}>Degraded Status:</Text><Text style={styles.value}>{result.degraded ? 'Yes' : 'No'}</Text></View>
          <View style={styles.row}><Text style={styles.label}>Manual Review:</Text><Text style={styles.value}>{result.manual_review_recommended ? 'Recommended' : 'Not Required'}</Text></View>
        </View>

        {/* Failed Components */}
        {result.component_failures && result.component_failures.length > 0 && (
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { backgroundColor: '#fee2e2', color: '#991b1b' }]}>Failed Components</Text>
            {result.component_failures.map((f, i) => (
              <View key={i} style={{ marginBottom: 5 }}>
                <Text style={{ fontWeight: 'bold' }}>{f.component || 'Unknown'} - {f.severity || 'Unknown Severity'}</Text>
                <Text>{f.reason}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Document Verification */}
        {docVerifyTrace?.safe_output && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Document Verification</Text>
            <View style={styles.row}><Text style={styles.label}>Status:</Text><Text style={styles.value}>{docVerifyTrace.safe_output.status}</Text></View>
            <View style={styles.row}><Text style={styles.label}>Provided Types:</Text><Text style={styles.value}>{(docVerifyTrace.safe_output.provided || []).join(', ') || 'None'}</Text></View>
            <View style={styles.row}><Text style={styles.label}>Missing Types:</Text><Text style={styles.value}>{(docVerifyTrace.safe_output.missing || []).join(', ') || 'None'}</Text></View>
            {docVerifyTrace.safe_output.message && (
              <View style={styles.row}><Text style={styles.label}>Message:</Text><Text style={styles.value}>{docVerifyTrace.safe_output.message}</Text></View>
            )}
          </View>
        )}

        {/* Policy Evaluation */}
        {policyTrace?.safe_output && policyTrace.safe_output.checks && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Policy Evaluation</Text>
            <View style={styles.table}>
              <View style={styles.tableRow}>
                <View style={[styles.tableColHeader, { width: '40%' }]}><Text style={styles.tableCellHeader}>Rule</Text></View>
                <View style={[styles.tableColHeader, { width: '20%' }]}><Text style={styles.tableCellHeader}>Status</Text></View>
                <View style={[styles.tableColHeader, { width: '40%' }]}><Text style={styles.tableCellHeader}>Reason / Detail</Text></View>
              </View>
              {policyTrace.safe_output.checks.map((check: any, idx: number) => (
                <View style={styles.tableRow} key={idx}>
                  <View style={[styles.tableCol, { width: '40%' }]}><Text style={styles.tableCell}>{check.name}</Text></View>
                  <View style={[styles.tableCol, { width: '20%' }]}><Text style={styles.tableCell}>{check.ok ? 'PASS' : 'FAIL'}</Text></View>
                  <View style={[styles.tableCol, { width: '40%' }]}><Text style={styles.tableCell}>{check.details?.reason || 'N/A'}</Text></View>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Financial Breakdown (Line Items) */}
        {lineItems.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Line-item Evaluation</Text>
            <View style={styles.table}>
              <View style={styles.tableRow}>
                <View style={[styles.tableColHeader, { width: '40%' }]}><Text style={styles.tableCellHeader}>Description</Text></View>
                <View style={[styles.tableColHeader, { width: '15%' }]}><Text style={styles.tableCellHeader}>Claimed</Text></View>
                <View style={[styles.tableColHeader, { width: '15%' }]}><Text style={styles.tableCellHeader}>Status</Text></View>
                <View style={[styles.tableColHeader, { width: '15%' }]}><Text style={styles.tableCellHeader}>Approved</Text></View>
                <View style={[styles.tableColHeader, { width: '15%' }]}><Text style={styles.tableCellHeader}>Reason</Text></View>
              </View>
              {lineItems.map((item: any, idx: number) => (
                <View style={styles.tableRow} key={idx}>
                  <View style={[styles.tableCol, { width: '40%' }]}><Text style={styles.tableCell}>{item.description}</Text></View>
                  <View style={[styles.tableCol, { width: '15%' }]}><Text style={styles.tableCell}>{item.claimed_amount ? `₹${item.claimed_amount}` : '-'}</Text></View>
                  <View style={[styles.tableCol, { width: '15%' }]}><Text style={styles.tableCell}>{item.eligible ? 'Eligible' : 'Ineligible'}</Text></View>
                  <View style={[styles.tableCol, { width: '15%' }]}><Text style={styles.tableCell}>{item.approved_amount ? `₹${item.approved_amount}` : '-'}</Text></View>
                  <View style={[styles.tableCol, { width: '15%' }]}><Text style={styles.tableCell}>{item.reason || '-'}</Text></View>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Financial Calculation (Flow) */}
        {financeTrace?.safe_output?.breakdown && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Financial Calculation</Text>
            <View style={styles.row}><Text style={styles.label}>Claimed Amount:</Text><Text style={styles.value}>₹{financeTrace.safe_output.breakdown.claimed || '0'}</Text></View>
            <View style={styles.row}><Text style={styles.label}>Network Discount:</Text><Text style={styles.value}>- ₹{financeTrace.safe_output.breakdown.network_discount || '0'}</Text></View>
            <View style={styles.row}><Text style={styles.label}>Co-pay:</Text><Text style={styles.value}>- ₹{financeTrace.safe_output.breakdown.copay || '0'}</Text></View>
            <View style={styles.row}><Text style={[styles.label, { color: '#0f172a' }]}>Final Approved Amount:</Text><Text style={[styles.value, { fontWeight: 'bold' }]}>₹{financeTrace.safe_output.breakdown.approved || '0'}</Text></View>
          </View>
        )}

        {/* Fraud Analysis */}
        {fraudTrace?.safe_output && (
           <View style={styles.section}>
             <Text style={styles.sectionTitle}>Fraud Analysis</Text>
             <View style={styles.row}><Text style={styles.label}>Status:</Text><Text style={styles.value}>{fraudTrace.safe_output.ok === false ? 'Flags Raised' : fraudTrace.safe_output.ok === true ? 'Clear' : 'N/A'}</Text></View>
             {fraudTrace.safe_output.signals && fraudTrace.safe_output.signals.length > 0 && (
                <View style={{ marginTop: 5 }}>
                  <Text style={{ fontWeight: 'bold', marginBottom: 2 }}>Signals:</Text>
                  {fraudTrace.safe_output.signals.map((s: any, idx: number) => (
                    <Text key={idx}>• {s.type || s.reason || JSON.stringify(s)}</Text>
                  ))}
                </View>
             )}
             {fraudTrace.status === "DEGRADED" && (
                <Text style={{ marginTop: 5, color: '#991b1b' }}>Analysis was degraded/skipped.</Text>
             )}
           </View>
        )}

        {/* Audit Trace */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Processing Audit Trail</Text>
          {result.trace.map((t, idx) => (
            <View key={idx} style={{ marginBottom: 5, paddingBottom: 5, borderBottomWidth: 0.5, borderBottomColor: '#e2e8f0' }}>
              <Text style={{ fontWeight: 'bold' }}>{idx + 1}. {t.step} ({t.component}) - {t.status}</Text>
              {t.summary && <Text style={{ marginTop: 2 }}>{t.summary}</Text>}
              {t.reason_code && <Text style={{ color: '#991b1b' }}>Reason: {t.reason_code}</Text>}
              {t.error && <Text style={{ color: '#991b1b' }}>Error: {t.error}</Text>}
            </View>
          ))}
        </View>

        {/* Final Recommendation */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Final Recommendation</Text>
          {(result.manual_review_recommended || result.degraded) ? (
            <View style={styles.warningBox}>
              <Text style={styles.warningText}>Manual Review Recommended</Text>
              <Text style={{ marginTop: 5 }}>The system recommends human review due to incomplete processing, component failure, or a triggered policy rule.</Text>
            </View>
          ) : (
            <Text>No manual review required. Processed normally with high confidence.</Text>
          )}
        </View>

        {/* Footer */}
        <Text style={styles.footer} render={({ pageNumber, totalPages }) => (
          `Generated by Plum Claims AI | Page ${pageNumber} of ${totalPages}`
        )} fixed />
      </Page>
    </Document>
  );
}
