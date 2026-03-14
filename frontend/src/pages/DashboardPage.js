import React, { useState, useEffect, useRef } from 'react';
import { DashboardLayout } from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import { Upload, FileText, Activity, TrendingUp, Brain, GitBranch, FileDown, MessageSquare, Trash2, Play } from 'lucide-react';
import { uploadAPI, analysisAPI, chatAPI, reportAPI } from '../lib/api';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function DashboardPage() {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [analyses, setAnalyses] = useState([]);
  const [chatMessage, setChatMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const fileInputRef = useRef(null);
  const pollInterval = useRef(null);

  useEffect(() => {
    loadUploadedFiles();
    loadAnalyses();
    
    return () => {
      if (pollInterval.current) {
        clearInterval(pollInterval.current);
      }
    };
  }, []);

  const loadUploadedFiles = async () => {
    try {
      const response = await uploadAPI.listUploads();
      setUploadedFiles(response.data);
    } catch (error) {
      toast.error('Failed to load files');
    }
  };

  const loadAnalyses = async () => {
    try {
      const response = await analysisAPI.listAnalyses();
      setAnalyses(response.data);
    } catch (error) {
      console.error('Failed to load analyses');
    }
  };

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    setUploading(true);
    for (const file of files) {
      try {
        await uploadAPI.uploadFile(file);
        toast.success(`${file.name} uploaded`);
      } catch (error) {
        toast.error(`Failed to upload ${file.name}`);
      }
    }
    setUploading(false);
    loadUploadedFiles();
  };

  const handleFileSelect = (fileId) => {
    setSelectedFiles(prev => 
      prev.includes(fileId) 
        ? prev.filter(id => id !== fileId)
        : [...prev, fileId]
    );
  };

  const handleDeleteFile = async (fileId) => {
    try {
      await uploadAPI.deleteUpload(fileId);
      toast.success('File deleted');
      loadUploadedFiles();
      setSelectedFiles(prev => prev.filter(id => id !== fileId));
    } catch (error) {
      toast.error('Failed to delete file');
    }
  };

  const startAnalysis = async () => {
    if (selectedFiles.length === 0) {
      toast.error('Please select at least one file');
      return;
    }

    try {
      const response = await analysisAPI.startAnalysis(selectedFiles);
      const analysisId = response.data.id;
      toast.success('Analysis started');
      
      pollInterval.current = setInterval(async () => {
        try {
          const result = await analysisAPI.getAnalysis(analysisId);
          setCurrentAnalysis(result.data);
          
          if (result.data.status === 'completed' || result.data.status === 'failed') {
            clearInterval(pollInterval.current);
            if (result.data.status === 'completed') {
              toast.success('Analysis completed');
            } else {
              toast.error('Analysis failed');
            }
            loadAnalyses();
          }
        } catch (error) {
          clearInterval(pollInterval.current);
        }
      }, 2000);
      
    } catch (error) {
      toast.error('Failed to start analysis');
    }
  };

  const loadAnalysis = async (analysisId) => {
    try {
      const response = await analysisAPI.getAnalysis(analysisId);
      setCurrentAnalysis(response.data);
    } catch (error) {
      toast.error('Failed to load analysis');
    }
  };

  const handleChat = async () => {
    if (!chatMessage.trim()) return;

    const userMessage = chatMessage;
    setChatMessage('');
    setChatHistory(prev => [...prev, { role: 'user', content: userMessage }]);

    try {
      const response = await chatAPI.sendMessage(userMessage, currentAnalysis?.id);
      setChatHistory(prev => [...prev, { role: 'assistant', content: response.data.response }]);
    } catch (error) {
      toast.error('Chat failed');
      setChatHistory(prev => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error.' }]);
    }
  };

  const downloadReport = async (analysisId) => {
    try {
      const response = await reportAPI.downloadReport(analysisId);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `RCA_Report_${analysisId}.md`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Report downloaded');
    } catch (error) {
      toast.error('Failed to download report');
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="dashboard">
        <div>
          <h2 className="text-4xl font-bold font-heading tracking-tight mb-2">ROOT CAUSE ANALYSIS</h2>
          <p className="text-muted-foreground font-mono text-sm uppercase tracking-wider">AI-Powered Machine Failure Diagnosis</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          <div className="md:col-span-4">
            <Card className="p-6 card-industrial h-full">
              <div className="flex items-center gap-2 mb-6">
                <Upload className="w-5 h-5 text-primary" />
                <h3 className="text-xl font-bold font-heading tracking-tight">UPLOAD CENTER</h3>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileUpload}
                className="hidden"
                accept=".pdf,.csv,.xlsx,.txt,.docx"
              />

              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="w-full mb-4 rounded-sm"
                data-testid="upload-button"
              >
                {uploading ? 'Uploading...' : 'Select Files'}
              </Button>

              <div className="space-y-2 max-h-[400px] overflow-y-auto">
                {uploadedFiles.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-8">No files uploaded</p>
                ) : (
                  uploadedFiles.map(file => (
                    <div
                      key={file.id}
                      className={`flex items-center gap-3 p-3 rounded-sm border transition-colors ${
                        selectedFiles.includes(file.id)
                          ? 'border-primary bg-primary/10'
                          : 'border-border hover:border-primary/50'
                      }`}
                      data-testid={`file-item-${file.id}`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedFiles.includes(file.id)}
                        onChange={() => handleFileSelect(file.id)}
                        className="w-4 h-4"
                        data-testid={`file-checkbox-${file.id}`}
                      />
                      <FileText className="w-4 h-4 text-primary flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-mono truncate">{file.filename}</p>
                        <p className="text-xs text-muted-foreground">{(file.file_size / 1024).toFixed(1)} KB</p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteFile(file.id)}
                        className="flex-shrink-0"
                        data-testid={`delete-file-${file.id}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  ))
                )}
              </div>

              <Button
                onClick={startAnalysis}
                disabled={selectedFiles.length === 0 || (currentAnalysis?.status === 'processing')}
                className="w-full mt-4 rounded-sm"
                data-testid="start-analysis-button"
              >
                <Play className="w-4 h-4 mr-2" />
                Start Analysis
              </Button>
            </Card>
          </div>

          <div className="md:col-span-8">
            {currentAnalysis ? (
              <Card className="p-6 card-industrial">
                <Tabs defaultValue="overview" className="space-y-6">
                  <TabsList className="grid grid-cols-5 w-full">
                    <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
                    <TabsTrigger value="anomalies" data-testid="tab-anomalies">Anomalies</TabsTrigger>
                    <TabsTrigger value="hypotheses" data-testid="tab-hypotheses">Hypotheses</TabsTrigger>
                    <TabsTrigger value="ml" data-testid="tab-ml">ML Results</TabsTrigger>
                    <TabsTrigger value="chat" data-testid="tab-chat">Chat</TabsTrigger>
                  </TabsList>

                  <TabsContent value="overview" data-testid="overview-content">
                    <div className="space-y-6">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-mono uppercase text-muted-foreground">Analysis Progress</span>
                          <span className="text-lg font-mono font-bold">{currentAnalysis.progress}%</span>
                        </div>
                        <Progress value={currentAnalysis.progress} className="h-2" />
                        <p className="text-xs text-muted-foreground mt-1 font-mono">{currentAnalysis.status}</p>
                      </div>

                      {currentAnalysis.root_cause && (
                        <div className="space-y-4">
                          <div className="p-4 rounded-sm border border-primary bg-primary/10">
                            <h4 className="text-lg font-bold font-heading mb-2 text-primary">ROOT CAUSE</h4>
                            <p className="text-foreground mb-3">{currentAnalysis.root_cause.root_cause}</p>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-mono uppercase text-muted-foreground">Confidence:</span>
                              <span className="text-2xl font-mono font-bold text-primary">
                                {(currentAnalysis.root_cause.confidence_score * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>

                          <div>
                            <h4 className="text-sm font-mono uppercase text-muted-foreground mb-3">Evidence</h4>
                            <ul className="space-y-2">
                              {currentAnalysis.root_cause.evidence?.map((ev, idx) => (
                                <li key={idx} className="flex items-start gap-2 text-sm">
                                  <span className="text-primary mt-1">•</span>
                                  <span>{ev}</span>
                                </li>
                              ))}
                            </ul>
                          </div>

                          <div>
                            <h4 className="text-sm font-mono uppercase text-muted-foreground mb-3">Preventive Actions</h4>
                            <ul className="space-y-2">
                              {currentAnalysis.root_cause.preventive_actions?.map((action, idx) => (
                                <li key={idx} className="flex items-start gap-2 text-sm">
                                  <span className="text-accent mt-1">→</span>
                                  <span>{action}</span>
                                </li>
                              ))}
                            </ul>
                          </div>

                          <Button
                            onClick={() => downloadReport(currentAnalysis.id)}
                            className="w-full rounded-sm"
                            data-testid="download-report-button"
                          >
                            <FileDown className="w-4 h-4 mr-2" />
                            Download Report
                          </Button>
                        </div>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="anomalies" data-testid="anomalies-content">
                    <div className="space-y-4">
                      <h4 className="text-lg font-bold font-heading">Detected Anomalies</h4>
                      {currentAnalysis.anomalies && currentAnalysis.anomalies.length > 0 ? (
                        <div className="space-y-2 max-h-[500px] overflow-y-auto">
                          {currentAnalysis.anomalies.map((anomaly, idx) => (
                            <div key={idx} className="p-3 rounded-sm border border-border bg-muted/20">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-mono text-sm font-bold">{anomaly.parameter}</span>
                                <span className={`text-xs px-2 py-1 rounded-sm ${
                                  anomaly.severity === 'high' ? 'bg-destructive/20 text-destructive' : 'bg-accent/20 text-accent'
                                }`}>
                                  {anomaly.severity}
                                </span>
                              </div>
                              <div className="text-xs text-muted-foreground font-mono">
                                Value: {anomaly.value.toFixed(2)} | Threshold: {anomaly.threshold.toFixed(2)}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">No anomalies detected yet</p>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="hypotheses" data-testid="hypotheses-content">
                    <div className="space-y-4">
                      <h4 className="text-lg font-bold font-heading">Failure Hypotheses</h4>
                      {currentAnalysis.hypotheses && currentAnalysis.hypotheses.length > 0 ? (
                        <div className="space-y-4">
                          {currentAnalysis.hypotheses.map((hyp, idx) => (
                            <div key={idx} className="p-4 rounded-sm border border-border bg-muted/20">
                              <div className="flex items-start justify-between mb-2">
                                <h5 className="font-bold font-heading">{hyp.title}</h5>
                                <span className="text-lg font-mono font-bold text-primary">
                                  {(hyp.probability * 100).toFixed(0)}%
                                </span>
                              </div>
                              <p className="text-sm text-muted-foreground mb-3">{hyp.description}</p>
                              <div>
                                <span className="text-xs font-mono uppercase text-muted-foreground">Evidence:</span>
                                <ul className="mt-2 space-y-1">
                                  {hyp.evidence?.map((ev, eidx) => (
                                    <li key={eidx} className="text-xs flex items-start gap-2">
                                      <span className="text-primary">•</span>
                                      <span>{ev}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">No hypotheses generated yet</p>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="ml" data-testid="ml-content">
                    <div className="space-y-6">
                      <h4 className="text-lg font-bold font-heading">Machine Learning Validation</h4>
                      {currentAnalysis.ml_results && currentAnalysis.ml_results.length > 0 ? (
                        <div className="space-y-6">
                          {currentAnalysis.ml_results.map((result, idx) => (
                            <div key={idx} className="p-4 rounded-sm border border-border bg-muted/20">
                              <div className="flex items-center justify-between mb-4">
                                <h5 className="font-bold font-heading">{result.model_name}</h5>
                                <span className="text-xl font-mono font-bold text-primary">
                                  {(result.accuracy * 100).toFixed(1)}%
                                </span>
                              </div>
                              
                              <div>
                                <span className="text-xs font-mono uppercase text-muted-foreground mb-2 block">Feature Importance</span>
                                <div className="space-y-2">
                                  {Object.entries(result.feature_importance || {}).map(([feature, importance]) => (
                                    <div key={feature}>
                                      <div className="flex items-center justify-between text-xs mb-1">
                                        <span className="font-mono">{feature}</span>
                                        <span className="font-mono font-bold">{(importance * 100).toFixed(0)}%</span>
                                      </div>
                                      <Progress value={importance * 100} className="h-1" />
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground">No ML results available yet</p>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="chat" data-testid="chat-content">
                    <div className="space-y-4">
                      <div className="h-[400px] overflow-y-auto border border-border rounded-sm p-4 space-y-3">
                        {chatHistory.length === 0 ? (
                          <p className="text-sm text-muted-foreground text-center py-8">
                            Ask questions about your analysis results
                          </p>
                        ) : (
                          chatHistory.map((msg, idx) => (
                            <div
                              key={idx}
                              className={`p-3 rounded-sm ${
                                msg.role === 'user'
                                  ? 'bg-primary/10 ml-12'
                                  : 'bg-muted/20 mr-12'
                              }`}
                            >
                              <div className="text-xs font-mono uppercase text-muted-foreground mb-1">
                                {msg.role === 'user' ? 'You' : 'AI Assistant'}
                              </div>
                              <p className="text-sm">{msg.content}</p>
                            </div>
                          ))
                        )}
                      </div>

                      <div className="flex gap-2">
                        <Input
                          value={chatMessage}
                          onChange={(e) => setChatMessage(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && handleChat()}
                          placeholder="Ask about the analysis..."
                          data-testid="chat-input"
                          className="font-mono"
                        />
                        <Button onClick={handleChat} className="rounded-sm" data-testid="chat-send-button">
                          <MessageSquare className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </Card>
            ) : (
              <Card className="p-12 card-industrial text-center">
                <Activity className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-xl font-bold font-heading mb-2">No Active Analysis</h3>
                <p className="text-muted-foreground">Upload files and start an analysis to see results</p>
              </Card>
            )}
          </div>
        </div>

        {analyses.length > 0 && (
          <Card className="p-6 card-industrial">
            <h3 className="text-xl font-bold font-heading mb-4">RECENT ANALYSES</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {analyses.slice(0, 6).map(analysis => (
                <div
                  key={analysis.id}
                  className="p-4 rounded-sm border border-border hover:border-primary/50 cursor-pointer transition-colors"
                  onClick={() => loadAnalysis(analysis.id)}
                  data-testid={`analysis-${analysis.id}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono uppercase text-muted-foreground">
                      {new Date(analysis.created_at).toLocaleDateString()}
                    </span>
                    <span className={`text-xs px-2 py-1 rounded-sm ${
                      analysis.status === 'completed' ? 'bg-accent/20 text-accent' : 'bg-muted text-muted-foreground'
                    }`}>
                      {analysis.status}
                    </span>
                  </div>
                  <p className="text-sm font-mono truncate">{analysis.id}</p>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
