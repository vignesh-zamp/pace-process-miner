import React, { useEffect, useState } from 'react';
import { Clock, FileText, ChevronRight, ChevronDown, History, Calendar } from 'lucide-react';
import { clsx } from 'clsx';

interface Document {
    id: string; // absolute path
    company: string;
    filename: string;
    name: string;
    version: string;
    date: string;
    processing_time: number;
}

interface HistorySidebarProps {
    onSelectDoc: (content: string, time?: number) => void;
    refreshTrigger: number;
}

const HistorySidebar: React.FC<HistorySidebarProps> = ({ onSelectDoc, refreshTrigger }) => {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [groupedDocs, setGroupedDocs] = useState<Record<string, Document[]>>({});
    const [expandedCompanies, setExpandedCompanies] = useState<Record<string, boolean>>({});
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchHistory();
    }, [refreshTrigger]);

    const fetchHistory = async () => {
        setLoading(true);
        try {
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const res = await fetch(`${API_URL}/documents`);
            const data = await res.json();
            setDocuments(data.documents);

            // Group by company
            const groups: Record<string, Document[]> = {};
            data.documents.forEach((doc: Document) => {
                if (!groups[doc.company]) groups[doc.company] = [];
                groups[doc.company].push(doc);
            });
            setGroupedDocs(groups);

            // Auto expand if only one company
            if (Object.keys(groups).length === 1) {
                setExpandedCompanies({ [Object.keys(groups)[0]]: true });
            }
        } catch (e) {
            console.error("Failed to fetch history", e);
        } finally {
            setLoading(false);
        }
    };

    const toggleCompany = (company: string) => {
        setExpandedCompanies(prev => ({
            ...prev,
            [company]: !prev[company]
        }));
    };

    const handleDocClick = async (doc: Document) => {
        try {
            const relativePath = `${doc.company}/${doc.filename}`;
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const res = await fetch(`${API_URL}/document?path=${encodeURIComponent(relativePath)}`);

            if (!res.ok) throw new Error("Failed to load");

            const data = await res.json();
            onSelectDoc(data.content, doc.processing_time);
        } catch (e) {
            console.error("Error loading doc", e);
        }
    };

    return (
        <div className="w-80 h-full bg-slate-50 border-r border-slate-200 flex flex-col">
            <div className="p-4 border-b border-slate-200 bg-white">
                <div className="flex items-center gap-2 font-bold text-slate-800">
                    <History className="w-5 h-5 text-indigo-600" />
                    <h2>Process History</h2>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2">
                {loading && <div className="text-center p-4 text-slate-400 text-sm">Loading...</div>}

                {!loading && Object.keys(groupedDocs).length === 0 && (
                    <div className="text-center p-8 text-slate-400 text-sm">
                        No history yet. Upload a video to start.
                    </div>
                )}

                {Object.entries(groupedDocs).map(([company, docs]) => (
                    <div key={company} className="mb-2">
                        <button
                            onClick={() => toggleCompany(company)}
                            className="w-full flex items-center justify-between p-2 hover:bg-slate-100 rounded-lg text-left transition-colors"
                        >
                            <span className="font-semibold text-slate-700 text-sm">{company}</span>
                            {expandedCompanies[company] ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                        </button>

                        {expandedCompanies[company] && (
                            <div className="ml-2 pl-2 border-l-2 border-slate-200 mt-1 space-y-1">
                                {docs.map(doc => (
                                    <button
                                        key={doc.id}
                                        onClick={() => handleDocClick(doc)}
                                        className="w-full p-2 text-left hover:bg-white hover:shadow-sm rounded-md transition-all group"
                                    >
                                        <div className="font-medium text-slate-700 text-sm group-hover:text-indigo-600 truncate">
                                            {doc.name}
                                        </div>
                                        <div className="flex items-center gap-2 mt-1">
                                            <span className="text-[10px] font-bold text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">{doc.version}</span>
                                            <span className="text-[10px] text-slate-400 flex items-center gap-0.5">
                                                <Calendar className="w-3 h-3" /> {doc.date.split(' ')[0]}
                                            </span>
                                            {doc.processing_time > 0 && (
                                                <span className="text-[10px] text-green-600 flex items-center gap-0.5 ml-auto">
                                                    <Clock className="w-3 h-3" /> {doc.processing_time}s
                                                </span>
                                            )}
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
};

export default HistorySidebar;
