import React from 'react';
import LoadingAnimation from './LoadingAnimation';
import ResultsPanel from './ResultsPanel';
import { saveAs } from 'file-saver';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

const Dashboard = ({ results, isScanning, url }) => {
  const downloadCSV = () => {
    if (!results || !results.accessibilityReport?.issues) return;

    const sanitize = (str) => (str || "").replace(/[\n\r]+/g, ' ').replace(/"/g, '""');
    const header = "ID,Title,Severity,Description,Element,Suggestion\n";
    const rows = results.accessibilityReport.issues.map(issue =>
      `${issue.id},"${sanitize(issue.title)}",${issue.severity},"${sanitize(issue.description)}","${sanitize(issue.element)}","${sanitize(issue.suggestion)}"`
    );
    const csvContent = header + rows.join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    saveAs(blob, `AltTextReport-${new Date().toISOString().split('T')[0]}.csv`);
  };

  const downloadPDF = () => {
    if (!results || !results.accessibilityReport?.issues) return;

    const { url: scannedUrl, score, totalIssues, issues } = results.accessibilityReport;
    const doc = new jsPDF();

    // Title
    doc.setFontSize(18);
    doc.setTextColor(40);
    doc.text("Alt Text Accessibility Report", 14, 20);

    // Metadata section (no emojis)
    doc.setFontSize(12);
    doc.setTextColor(60);
    doc.text(`URL: ${scannedUrl}`, 14, 30);
    doc.text(`Score: ${score}`, 14, 37);
    doc.text(`Total Issues: ${totalIssues}`, 14, 44);
    doc.text(`Date: ${new Date().toLocaleString()}`, 14, 51);

    // Table of issues
    const tableData = issues.map((issue, index) => [
      index + 1,
      issue.title,
      issue.severity,
      issue.description,
      issue.element,
      issue.suggestion,
    ]);

    autoTable(doc, {
      startY: 60,
      head: [['#', 'Title', 'Severity', 'Description', 'Element', 'Suggestion']],
      body: tableData,
      styles: {
        fontSize: 9,
        cellPadding: 3,
      },
      headStyles: {
        fillColor: [33, 150, 243],
        textColor: 255,
        fontStyle: 'bold',
      },
      alternateRowStyles: {
        fillColor: [245, 245, 245],
      },
      columnStyles: {
        0: { cellWidth: 10 },
        1: { cellWidth: 35 },
        2: { cellWidth: 20 },
        3: { cellWidth: 45 },
        4: { cellWidth: 35 },
        5: { cellWidth: 45 },
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
            <div className="flex justify-end mb-4 space-x-4 no-print">
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
              <ResultsPanel results={results} />
            </div>
          </>
        )}
      </div>
    </section>
  );
};

export default Dashboard;
