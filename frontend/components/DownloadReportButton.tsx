"use client";

import React, { useState, useEffect } from "react";
import { PDFDownloadLink } from "@react-pdf/renderer";
import { ClaimReportPDF } from "./ClaimReportPDF";
import type { ClaimSubmission, ClaimProcessingResult } from "../app/types";
import { Download } from "lucide-react";

interface DownloadReportButtonProps {
  submission: ClaimSubmission;
  result: ClaimProcessingResult;
}

export function DownloadReportButton({ submission, result }: DownloadReportButtonProps) {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  if (!isClient) {
    return null; // Prevents hydration error since PDFDownloadLink doesn't work well server-side
  }

  return (
    <div className="mt-6 flex justify-end">
      <PDFDownloadLink
        document={<ClaimReportPDF submission={submission} result={result} />}
        fileName={`plum-claim-report-${result.claim_id}.pdf`}
        className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white font-medium py-2 px-4 rounded-lg transition-colors"
      >
        {({ loading }) => (
          <>
            <Download className="w-4 h-4" />
            {loading ? "Generating PDF..." : "Download Report (PDF)"}
          </>
        )}
      </PDFDownloadLink>
    </div>
  );
}
