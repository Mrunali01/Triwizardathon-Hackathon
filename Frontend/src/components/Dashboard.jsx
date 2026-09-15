import React from 'react';
import LoadingAnimation from './LoadingAnimation';
import ResultsPanel from './ResultsPanel';
import { saveAs } from 'file-saver';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const Dashboard = ({ results, isScanning, url, altTextLoading }) => {
  const downloadCSV = () => {
    if (!results || !results.accessibilityReport?.issues) return;

    const report = results.accessibilityReport;
    const sanitize = (value) => {
      let text = String(value ?? '').replace(/[\n\r]+/g, ' ');
      if (/^[=+@\-\t]/.test(text)) text = "'" + text;
      return `"${text.replace(/"/g, '""')}"`;
    };
    const header = ['ID', 'Title', 'Severity', 'Description', 'Element', 'Suggestion', 'WCAG', 'Why it matters', 'Why the fix helps', 'Confidence', 'Sources', 'Before score', 'After score'];
    const rows = report.issues.map(issue => [issue.id, issue.title, issue.type, issue.description, issue.element, issue.suggestion, issue.wcagReference, issue.explanation?.why_it_matters, issue.explanation?.reasoning_summary, issue.explanation?.confidence, issue.explanation?.evidence.map(e => e.source).join('; '), report.comparison?.beforeScore, report.comparison?.afterScore]);
    if (report.comparison && !rows.length) rows.push(Array(11).fill('').concat([report.comparison.beforeScore, report.comparison.afterScore]));
    const csvContent = [header, ...rows].map(row => row.map(sanitize).join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    saveAs(blob, `AltTextReport-${new Date().toISOString().split('T')[0]}.csv`);
  };

  const downloadPDF = () => {
    if (!results || !results.accessibilityReport?.issues) return;

    const { url: scannedUrl, score, totalIssues, issues } = results.accessibilityReport;
    const doc = new jsPDF();
    doc.setFontSize(18);
    doc.setTextColor(40);
    doc.text("Alt Text Accessibility Report", 14, 20);
    doc.setFontSize(12);
    doc.setTextColor(60);
    doc.text(`URL: ${scannedUrl}`, 14, 30);
    doc.text(`Score: ${score}`, 14, 37);
    doc.text(`Total Issues: ${totalIssues}`, 14, 44);
    doc.text(`Date: ${new Date().toLocaleString()}`, 14, 51);
    if (results.accessibilityReport.comparison) {
      const c = results.accessibilityReport.comparison;
      doc.text(`Before: ${c.beforeScore} / After: ${c.afterScore} / Change: ${c.scoreChange}`, 14, 58);
    }
    const tableData = issues.map((issue, index) => [
      index + 1,
      issue.title,
      issue.severity,
      `${issue.description}\n${issue.explanation?.why_it_matters || ''}\n${issue.wcagReference || ''}\nConfidence: ${issue.explanation?.confidence || 'Unavailable'}`,
      issue.element,
      `${issue.suggestion}\n${issue.explanation?.reasoning_summary || ''}\n${issue.explanation?.evidence.map(e => e.source).join('\n') || ''}`,
    ]);
    autoTable(doc, {
      startY: 65,
      head: [['#', 'Title', 'Severity', 'Description', 'Element', 'Suggestion']],
      body: tableData,
      styles: { fontSize: 9, cellPadding: 3 },
      headStyles: { fillColor: [33, 150, 243], textColor: 255, fontStyle: 'bold' },
      alternateRowStyles: { fillColor: [245, 245, 245] },
      columnStyles: {
        0: { cellWidth: 10 }, 1: { cellWidth: 28 }, 2: { cellWidth: 17 },
        3: { cellWidth: 42 }, 4: { cellWidth: 35 }, 5: { cellWidth: 40 },
      },
      margin: { top: 60 },
    });
    doc.save(`AccessibilityReport-${new Date().toISOString().split('T')[0]}.pdf`);
  };


  const printReport = () => {
    window.print();
  };

  return (
    <section className="mt-12 print:bg-white print:text-black">
      <div className="bg-gray-900/40 backdrop-blur-xl border border-blue-500/20 rounded-3xl p-6 sm:p-8 lg:p-12 shadow-2xl shadow-blue-500/5 print:shadow-none print:bg-white print:p-0 print:border-none">
        {isScanning ? (
          <LoadingAnimation url={url} />
        ) : (
          <>
            {/* Buttons */}
            <div className="flex flex-wrap justify-end mb-4 gap-3 no-print">
              <button
                onClick={downloadPDF}
                className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded-lg transition"
              >
                Download PDF
              </button>
              <button
                onClick={downloadCSV}
                className="bg-green-600 hover:bg-green-700 text-white font-medium px-4 py-2 rounded-lg transition"
              >
                Download CSV
              </button>
              <button
                onClick={printReport}
                className="bg-yellow-600 hover:bg-yellow-700 text-white font-medium px-4 py-2 rounded-lg transition"
              >
                Print Report
              </button>
            </div>

            {/* Result Panel */}
            <div id="printable-report">
              <ResultsPanel key={results.accessibilityReport?.scanId} results={results} altTextLoading={altTextLoading} />
            </div>
          </>
        )}
      </div>
    </section>
  );
};

export default Dashboard;
