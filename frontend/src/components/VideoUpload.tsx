import React, { useState, useCallback } from 'react';
import { Upload, FileVideo, FileText, FileAudio, Image as ImageIcon, X, Loader2, AlertCircle, PlayCircle, Layers } from 'lucide-react';
import { twMerge } from 'tailwind-merge';

interface VideoUploadProps {
    onSopGenerated: (sop: string, time?: number) => void;
    isLoading: boolean;
    setIsLoading: (loading: boolean) => void;
}

const VideoUpload: React.FC<VideoUploadProps> = ({ onSopGenerated, isLoading, setIsLoading }) => {
    const [error, setError] = useState<string | null>(null);
    const [dragActive, setDragActive] = useState(false);
    const [selectedFiles, setSelectedFiles] = useState<{ file: File; context: string }[]>([]);

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    }, []);

    const handleFiles = (files: FileList | null) => {
        if (!files) return;
        const newFiles = Array.from(files).map(file => ({ file, context: '' }));
        setSelectedFiles(prev => [...prev, ...newFiles]);
        setError(null);
    };

    const removeFile = (index: number) => {
        setSelectedFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleUpload = async () => {
        if (selectedFiles.length === 0) return;

        setIsLoading(true);
        setError(null);

        const formData = new FormData();
        const contextMap: Record<string, string> = {};

        selectedFiles.forEach(({ file, context }) => {
            formData.append('files', file);
            contextMap[file.name] = context;
        });

        formData.append('file_contexts', JSON.stringify(contextMap));

        try {
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
            const response = await fetch(`${API_URL}/analyze`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Error: ${response.statusText}`);
            }

            const data = await response.json();
            if (['success', 'created', 'updated'].includes(data.status)) {
                onSopGenerated(data.sop, data.processing_time);
                setSelectedFiles([]); // Clear on success
            } else {
                throw new Error(data.message || 'Unknown error');
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Upload failed');
        } finally {
            setIsLoading(false);
        }
    };

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        handleFiles(e.dataTransfer.files);
    }, []);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        handleFiles(e.target.files);
    };

    const getFileIcon = (type: string) => {
        if (type.startsWith('video/')) return <FileVideo className="w-5 h-5 text-purple-500" />;
        if (type.startsWith('audio/')) return <FileAudio className="w-5 h-5 text-amber-500" />;
        if (type.startsWith('image/')) return <ImageIcon className="w-5 h-5 text-emerald-500" />;
        return <FileText className="w-5 h-5 text-blue-500" />;
    };

    return (
        <div className="w-full space-y-6">
            {/* Upload Area */}
            <div
                className={twMerge(
                    "relative group cursor-pointer transition-all duration-300 ease-in-out min-h-[250px] flex flex-col items-center justify-center",
                    "rounded-xl border-2 border-dashed",
                    isLoading ? "opacity-50 pointer-events-none border-blue-200 bg-slate-50" : "hover:border-blue-500 hover:bg-blue-50/50",
                    dragActive ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-slate-50"
                )}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-input')?.click()}
            >
                <input
                    id="file-input"
                    type="file"
                    className="hidden"
                    onChange={handleChange}
                    multiple
                    accept="video/*,audio/*,image/*,.pdf,.txt,.md"
                    disabled={isLoading}
                />

                <div className="flex flex-col items-center justify-center text-center space-y-4 p-8 pointer-events-none">
                    <div className={twMerge(
                        "p-4 rounded-full transition-colors duration-300 shadow-sm",
                        dragActive ? "bg-white text-blue-600" : "bg-white text-slate-400 group-hover:text-blue-600 group-hover:scale-110 transform"
                    )}>
                        <Upload className="w-10 h-10" />
                    </div>
                    <div>
                        <h3 className="text-xl font-bold text-slate-800 mb-1">
                            Upload Evidence
                        </h3>
                        <p className="text-slate-500 font-medium text-sm">
                            Drop Videos, Audio, PDFs, or Images here.
                        </p>
                    </div>
                    <div className="flex flex-wrap justify-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-widest bg-white/50 px-3 py-1.5 rounded-md">
                        <span className="flex items-center gap-1"><FileVideo className="w-3 h-3" /> MP4</span>
                        <span className="flex items-center gap-1"><FileAudio className="w-3 h-3" /> MP3</span>
                        <span className="flex items-center gap-1"><FileText className="w-3 h-3" /> PDF</span>
                        <span className="flex items-center gap-1"><ImageIcon className="w-3 h-3" /> IMG</span>
                    </div>
                </div>
            </div>

            {/* Evidence List */}
            {selectedFiles.length > 0 && (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden animate-in fade-in slide-in-from-top-4">
                    <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
                        <h4 className="font-semibold text-slate-700 flex items-center gap-2">
                            <Layers className="w-4 h-4 text-blue-600" />
                            Evidence Board ({selectedFiles.length})
                        </h4>
                        <button
                            onClick={handleUpload}
                            disabled={isLoading}
                            className="text-xs font-bold bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2 disabled:opacity-50"
                        >
                            {isLoading ? <Loader2 className="w-3 h-3 animate-spin" /> : <PlayCircle className="w-3 h-3" />}
                            {isLoading ? 'ANALYZING...' : 'ANALYZE EVIDENCE'}
                        </button>
                    </div>
                    <div className="divide-y divide-slate-100 max-h-60 overflow-y-auto">
                        {selectedFiles.map((file, idx) => (
                            <div key={idx} className="flex items-center justify-between p-3 hover:bg-slate-50 group">
                                <div className="flex items-center gap-3 overflow-hidden">
                                    <div className="p-2 bg-slate-100 rounded-lg">
                                        {getFileIcon(file.file.type)}
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <p className="text-sm font-medium text-slate-700 truncate">{file.file.name}</p>
                                        <div className="flex items-center gap-2 mt-1">
                                            <p className="text-xs text-slate-400">{(file.file.size / 1024 / 1024).toFixed(2)} MB</p>
                                            <input
                                                type="text"
                                                placeholder="Add context (optional)..."
                                                value={file.context}
                                                onChange={(e) => {
                                                    const newFiles = [...selectedFiles];
                                                    newFiles[idx].context = e.target.value;
                                                    setSelectedFiles(newFiles);
                                                }}
                                                className="text-xs px-2 py-0.5 border border-slate-200 rounded min-w-[200px] text-slate-600 focus:outline-none focus:border-blue-500"
                                                onClick={(e) => e.stopPropagation()}
                                            />
                                        </div>
                                    </div>
                                </div>
                                <button
                                    onClick={() => removeFile(idx)}
                                    disabled={isLoading}
                                    className="p-2 text-slate-300 hover:text-red-500 rounded-full hover:bg-red-50 transition-colors"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Error Message */}
            {error && (
                <div className="mt-4 flex items-center gap-3 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100 animate-in fade-in slide-in-from-top-2">
                    <AlertCircle className="w-5 h-5 shrink-0" />
                    <p className="text-sm font-medium">{error}</p>
                </div>
            )}

            {/* Loading State Overlay */}
            {isLoading && (
                <div className="fixed inset-0 bg-white/80 backdrop-blur-sm z-50 flex flex-col items-center justify-center">
                    <div className="p-4 bg-white rounded-full mb-6 shadow-xl animate-bounce">
                        <Layers className="w-12 h-12 text-blue-600" />
                    </div>
                    <h3 className="text-2xl font-bold text-slate-800 mb-2">Analysis in Progress...</h3>
                    <p className="text-slate-500 font-medium max-w-md text-center">
                        Synthesizing insights from {selectedFiles.length} evidence sources. Please wait.
                    </p>
                </div>
            )}
        </div>
    );
};

export default VideoUpload;
