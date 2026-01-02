
import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Copy, FileText, Check, Download, Clock } from 'lucide-react';
// @ts-ignore
import html2pdf from 'html2pdf.js';
import remarkGfm from 'remark-gfm';

interface SOPViewerProps {
    content: string;
    processingTime?: number;
}

const SOPViewer: React.FC<SOPViewerProps> = ({ content, processingTime }) => {
    const [copied, setCopied] = useState(false);

    if (!content) return null;

    const handleCopy = () => {
        navigator.clipboard.writeText(content);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleDownload = () => {
        const element = document.getElementById('sop-content');
        const opt = {
            margin: 1,
            filename: 'SOP_Document.pdf',
            image: { type: 'jpeg', quality: 0.98 },
            html2canvas: { scale: 2 },
            jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
        };
        html2pdf().set(opt).from(element).save();
    };

    return (
        <div className="w-full max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="bg-white rounded-2xl shadow-xl shadow-slate-200/50 overflow-hidden border border-slate-100">

                {/* Header */}
                <div className="flex items-center justify-between px-8 py-5 border-b border-slate-100 bg-slate-50/50 backdrop-blur-sm">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-indigo-100/50 rounded-lg">
                            <FileText className="w-5 h-5 text-indigo-600" />
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <h2 className="text-lg font-bold text-slate-800">Generated SOP</h2>
                                {processingTime && (
                                    <span className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-green-100 text-green-700 text-xs font-semibold border border-green-200">
                                        <Clock className="w-3 h-3" />
                                        {processingTime}s
                                    </span>
                                )}
                            </div>
                            <p className="text-xs text-slate-500 font-medium">AI-Synthesized Documentation</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleCopy}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-all"
                        >
                            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                            {copied ? 'Copied' : 'Copy Text'}
                        </button>
                        <button
                            onClick={handleDownload}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-all shadow-lg shadow-slate-900/10"
                        >
                            <Download className="w-4 h-4" />
                            Export PDF
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="p-8 md:p-10" id="sop-content">
                    <div className="prose prose-slate max-w-none prose-headings:font-bold prose-headings:text-slate-800 prose-p:text-slate-600 prose-li:text-slate-600 prose-strong:text-indigo-900 prose-strong:font-semibold prose-table:border-collapse prose-th:bg-slate-100 prose-th:p-4 prose-th:text-left prose-td:p-4 prose-td:border-b prose-td:border-slate-100">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SOPViewer;
