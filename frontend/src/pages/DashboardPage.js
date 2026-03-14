import React, { useState, useEffect, useRef } from 'react';
import { DashboardLayout } from '../components/DashboardLayout';
import { Button } from '../components/ui/button';
import { Card } from '../components/ui/card';
import { Progress } from '../components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import { Upload, FileText, Activity, TrendingUp, Brain, GitBranch, FileDown, MessageSquare, Trash2, Play, Clock, BarChart3, TrendingDown } from 'lucide-react';
import { uploadAPI, analysisAPI, chatAPI, reportAPI } from '../lib/api';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter, Cell } from 'recharts';

export default function DashboardPage() {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [projectName, setProjectName] = useState('');
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

  const handleDeleteAnalysis = async (analysisId, e) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this analysis?')) {
      return;
    }
    
    try {
      await analysisAPI.deleteAnalysis(analysisId);
      toast.success('Analysis deleted');
      loadAnalyses();
      if (currentAnalysis?.id === analysisId) {
        setCurrentAnalysis(null);
      }
    } catch (error) {
      toast.error('Failed to delete analysis');
    }
  };

  const startAnalysis = async () => {
    if (selectedFiles.length === 0) {
      toast.error('Please select at least one file');
      return;
    }

    if (!projectName.trim()) {
      toast.error('Please enter a project name');
      return;
    }

    try {
      const response = await analysisAPI.startAnalysis(selectedFiles, projectName);
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
      window.URL.revokeObjectURL(url);
      toast.success('Report downloaded');
    } catch (error) {
      toast.error('Failed to download report');
    }
  };

  const formatTimeRemaining = (seconds) => {
    if (!seconds || seconds <= 0) return '';
    return seconds < 60 ? `~${seconds}s` : `~${Math.ceil(seconds / 60)}m`;
  };

  return (
    <DashboardLayout>
      <div className="space-y-6" data-testid="dashboard">
        <div>
          <h2 className="text-3xl font-bold tracking-tight mb-2">Root Cause Analysis</h2>
          <p className="text-muted-foreground text-sm">CauseSense AI - Machine Failure Diagnosis & Process Data Analysis</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Upload & Control Panel */}
          <div className="lg:col-span-4">
            <Card className="p-6 data-card h-full">
              <div className="flex items-center gap-2 mb-6">
                <Upload className="w-5 h-5 text-primary" />
                <h3 className="text-lg font-semibold">Upload Center</h3>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="metric-label block mb-2">Project Name</label>
                  <Input
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    placeholder="e.g., Pump Failure Analysis"
                    data-testid="project-name-input"
                    className="h-10"
                  />
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
                  variant="outline"
                  className="w-full"
                  data-testid="upload-button"
                >
                  {uploading ? 'Uploading...' : 'Select Files'}
                </Button>

                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {uploadedFiles.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-8">No files uploaded</p>
                  ) : (
                    uploadedFiles.map(file => (
                      <div
                        key={file.id}
                        className={`flex items-center gap-3 p-3 rounded-md border transition-colors ${
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
                          <p className="text-sm font-medium truncate">{file.filename}</p>
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
                  disabled={selectedFiles.length === 0 || !projectName.trim() || (currentAnalysis?.status === 'processing')}
                  className="w-full"
                  data-testid="start-analysis-button"
                >
                  <Play className="w-4 h-4 mr-2" />
                  Start Analysis
                </Button>
              </div>
            </Card>
          </div>

          {/* Analysis Results Panel */}
          <div className="lg:col-span-8">
            {currentAnalysis ? (
              <Card className="p-6 data-card">
                <Tabs defaultValue="overview" className="space-y-6">
                  <TabsList className="grid grid-cols-6 w-full">
                    <TabsTrigger value="overview" data-testid="tab-overview">Overview</TabsTrigger>
                    <TabsTrigger value="visualizations" data-testid="tab-visualizations">
                      <BarChart3 className="w-4 h-4 mr-1" />
                      Charts
                    </TabsTrigger>
                    <TabsTrigger value="anomalies" data-testid="tab-anomalies">Anomalies</TabsTrigger>
                    <TabsTrigger value="hypotheses" data-testid="tab-hypotheses">Hypotheses</TabsTrigger>
                    <TabsTrigger value="ml" data-testid="tab-ml">ML</TabsTrigger>
                    <TabsTrigger value="chat" data-testid="tab-chat">Chat</TabsTrigger>
                  </TabsList>

                  <TabsContent value="overview" data-testid="overview-content">
                    <div className="space-y-6">
                      <div>
                        <div className="flex items-center justify-between mb-3">
                          <div>
                            <h3 className="text-lg font-semibold">{currentAnalysis.project_name}</h3>
                            <p className="text-xs text-muted-foreground">
                              Started: {new Date(currentAnalysis.created_at).toLocaleString()}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className={`status-badge ${
                              currentAnalysis.status === 'completed' ? 'bg-accent/20 text-accent' :
                              currentAnalysis.status === 'processing' ? 'bg-primary/20 text-primary' :
                              'bg-destructive/20 text-destructive'
                            }`}>
                              {currentAnalysis.status}
                            </span>
                          </div>
                        </div>

                        <Progress value={currentAnalysis.progress} className="h-3 mb-2" />
                        
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-mono font-bold text-lg">{currentAnalysis.progress}%</span>
                          <div className="flex items-center gap-2 text-muted-foreground">
                            {currentAnalysis.current_step && (
                              <>
                                <span>{currentAnalysis.current_step}</span>
                                {currentAnalysis.estimated_time_remaining > 0 && (
                                  <>
                                    <Clock className="w-4 h-4" />
                                    <span className="font-mono">{formatTimeRemaining(currentAnalysis.estimated_time_remaining)}</span>
                                  </>
                                )}
                              </>
                            )}
                          </div>
                        </div>
                      </div>

                      {currentAnalysis.root_cause && (
                        <div className="space-y-4">
                          <div className="p-5 rounded-md border-2 border-primary bg-primary/5">
                            <h4 className="text-sm font-medium text-primary uppercase tracking-wide mb-3">Root Cause Identified</h4>
                            <p className="text-base font-medium mb-4">{currentAnalysis.root_cause.root_cause}</p>
                            <div className="flex items-center gap-3">
                              <span className="metric-label">Confidence</span>
                              <div className="flex items-center gap-2">
                                <Progress value={currentAnalysis.root_cause.confidence_score * 100} className="h-2 w-32" />
                                <span className="metric-value text-xl">{(currentAnalysis.root_cause.confidence_score * 100).toFixed(0)}%</span>
                              </div>
                            </div>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="p-4 rounded-md bg-secondary border border-border">
                              <h4 className="metric-label mb-3">Evidence</h4>
                              <ul className="space-y-2">
                                {currentAnalysis.root_cause.evidence?.slice(0, 3).map((ev, idx) => (
                                  <li key={idx} className="flex items-start gap-2 text-sm">
                                    <span className="text-primary mt-1">•</span>
                                    <span>{ev}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>

                            <div className="p-4 rounded-md bg-secondary border border-border">
                              <h4 className="metric-label mb-3">Preventive Actions</h4>
                              <ul className="space-y-2">
                                {currentAnalysis.root_cause.preventive_actions?.slice(0, 3).map((action, idx) => (
                                  <li key={idx} className="flex items-start gap-2 text-sm">
                                    <span className="text-accent mt-1">→</span>
                                    <span>{action}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          </div>

                          <Button
                            onClick={() => downloadReport(currentAnalysis.id)}
                            className="w-full"
                            data-testid="download-report-button"
                          >
                            <FileDown className="w-4 h-4 mr-2" />
                            Download Complete Report
                          </Button>
                        </div>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="visualizations" data-testid="visualizations-content">
                    <div className="space-y-6">
                      <h4 className="text-lg font-semibold">Process Data Visualizations</h4>

                      {currentAnalysis.visualizations?.time_series && currentAnalysis.visualizations.time_series.length > 0 && (
                        <div className="p-4 rounded-md bg-secondary border border-border">
                          <h5 className="metric-label mb-4">Time-Series Data</h5>
                          <ResponsiveContainer width="100%" height={300}>
                            <LineChart data={currentAnalysis.visualizations.time_series}>
                              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                              <XAxis dataKey="index" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 12 }} />
                              <YAxis stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 12 }} />
                              <Tooltip 
                                contentStyle={{ 
                                  backgroundColor: 'hsl(var(--card))', 
                                  border: '1px solid hsl(var(--border))',
                                  borderRadius: '6px'
                                }} 
                              />
                              <Legend />
                              {Object.keys(currentAnalysis.visualizations.time_series[0] || {})
                                .filter(key => key !== 'index')
                                .slice(0, 5)
                                .map((key, idx) => (
                                  <Line 
                                    key={key} 
                                    type="monotone" 
                                    dataKey={key} 
                                    stroke={['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'][idx % 5]} 
                                    strokeWidth={2}
                                  />
                                ))}
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      )}

                      {currentAnalysis.visualizations?.feature_importance && currentAnalysis.visualizations.feature_importance.length > 0 && (
                        <div className="p-4 rounded-md bg-secondary border border-border">
                          <h5 className="metric-label mb-4">Feature Importance (ML Analysis)</h5>
                          <ResponsiveContainer width="100%" height={300}>
                            <BarChart data={currentAnalysis.visualizations.feature_importance} layout="vertical">
                              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                              <XAxis type="number" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 12 }} />
                              <YAxis dataKey="parameter" type="category" stroke="hsl(var(--muted-foreground))" tick={{ fontSize: 12 }} width={100} />
                              <Tooltip 
                                contentStyle={{ 
                                  backgroundColor: 'hsl(var(--card))', 
                                  border: '1px solid hsl(var(--border))',
                                  borderRadius: '6px'
                                }} 
                              />
                              <Bar dataKey="importance" fill="#3b82f6" />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      )}

                      {currentAnalysis.visualizations?.correlation && currentAnalysis.visualizations.correlation.correlations && (
                        <div className="p-4 rounded-md bg-secondary border border-border">
                          <h5 className="metric-label mb-4">Parameter Correlations</h5>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[300px] overflow-y-auto">
                            {currentAnalysis.visualizations.correlation.correlations
                              .sort((a, b) => Math.abs(b.correlation) - Math.abs(a.correlation))
                              .slice(0, 10)
                              .map((corr, idx) => (
                                <div key={idx} className="p-3 rounded-md bg-card border border-border">
                                  <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm font-medium">{corr.param1} ↔ {corr.param2}</span>
                                    <span className={`text-sm font-mono font-bold ${
                                      Math.abs(corr.correlation) > 0.7 ? 'text-primary' : 'text-muted-foreground'
                                    }`}>
                                      {corr.correlation.toFixed(2)}
                                    </span>
                                  </div>
                                  <Progress value={Math.abs(corr.correlation) * 100} className="h-1" />
                                </div>
                              ))}
                          </div>
                        </div>
                      )}

                      {(!currentAnalysis.visualizations || 
                        (!currentAnalysis.visualizations.time_series?.length && 
                         !currentAnalysis.visualizations.feature_importance?.length)) && (
                        <p className="text-sm text-muted-foreground text-center py-8">
                          Visualizations will appear once analysis is complete
                        </p>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="anomalies" data-testid="anomalies-content">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <h4 className="text-lg font-semibold">Detected Anomalies</h4>
                        {currentAnalysis.anomalies && (
                          <span className="metric-label">{currentAnalysis.anomalies.length} found</span>
                        )}
                      </div>

                      {currentAnalysis.anomalies && currentAnalysis.anomalies.length > 0 ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[500px] overflow-y-auto">
                          {currentAnalysis.anomalies.map((anomaly, idx) => (
                            <div key={idx} className="p-4 rounded-md border border-border bg-secondary">
                              <div className="flex items-center justify-between mb-2">
                                <span className="font-mono text-sm font-bold text-primary">{anomaly.parameter}</span>
                                <span className={`status-badge ${
                                  anomaly.severity === 'high' ? 'bg-destructive/20 text-destructive' : 'bg-warning/20 text-[hsl(var(--warning))]'
                                }`}>
                                  {anomaly.severity}
                                </span>
                              </div>
                              
                              {anomaly.timestamp && (
                                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                                  <Clock className="w-3 h-3" />
                                  <span>{anomaly.timestamp}</span>
                                </div>
                              )}

                              <div className="space-y-1 text-xs">
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Value:</span>
                                  <span className="font-mono font-bold">{anomaly.value.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Threshold:</span>
                                  <span className="font-mono">{anomaly.threshold.toFixed(2)}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Deviation:</span>
                                  <span className="font-mono text-destructive">
                                    {((anomaly.value / anomaly.threshold - 1) * 100).toFixed(0)}%
                                  </span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground text-center py-8">No anomalies detected yet</p>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="hypotheses" data-testid="hypotheses-content">
                    <div className="space-y-4">
                      <h4 className="text-lg font-semibold">Failure Hypotheses</h4>
                      {currentAnalysis.hypotheses && currentAnalysis.hypotheses.length > 0 ? (
                        <div className="space-y-4">
                          {currentAnalysis.hypotheses.map((hyp, idx) => (
                            <div key={idx} className="p-4 rounded-md border border-border bg-secondary">
                              <div className="flex items-start justify-between mb-2">
                                <h5 className="font-semibold text-primary">{hyp.title}</h5>
                                <div className="flex items-center gap-2">
                                  <Progress value={hyp.probability * 100} className="h-2 w-20" />
                                  <span className="text-lg font-mono font-bold text-primary">
                                    {(hyp.probability * 100).toFixed(0)}%
                                  </span>
                                </div>
                              </div>
                              <p className="text-sm text-muted-foreground mb-3">{hyp.description}</p>
                              <div>
                                <span className="metric-label">Evidence:</span>
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
                        <p className="text-sm text-muted-foreground text-center py-8">No hypotheses generated yet</p>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="ml" data-testid="ml-content">
                    <div className="space-y-6">
                      <h4 className="text-lg font-semibold">Machine Learning Validation</h4>
                      {currentAnalysis.ml_results && currentAnalysis.ml_results.length > 0 ? (
                        <div className="space-y-4">
                          {currentAnalysis.ml_results.map((result, idx) => (
                            <div key={idx} className="p-4 rounded-md border border-border bg-secondary">
                              <div className="flex items-center justify-between mb-4">
                                <h5 className="font-semibold">{result.model_name}</h5>
                                <div className="flex items-center gap-2">
                                  <span className="metric-label">Accuracy</span>
                                  <span className="metric-value text-xl text-primary">
                                    {(result.accuracy * 100).toFixed(1)}%
                                  </span>
                                </div>
                              </div>
                              
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                  <span className="metric-label mb-2 block">Feature Importance</span>
                                  <div className="space-y-2">
                                    {Object.entries(result.feature_importance || {}).map(([feature, importance]) => (
                                      <div key={feature}>
                                        <div className="flex items-center justify-between text-xs mb-1">
                                          <span className="font-mono">{feature}</span>
                                          <span className="font-mono font-bold">{(importance * 100).toFixed(0)}%</span>
                                        </div>
                                        <Progress value={importance * 100} className="h-2" />
                                      </div>
                                    ))}
                                  </div>
                                </div>

                                {result.confusion_matrix && (
                                  <div>
                                    <span className="metric-label mb-2 block">Confusion Matrix</span>
                                    <div className="grid grid-cols-2 gap-2">
                                      <div className="p-3 rounded-md bg-accent/10 border border-accent/20 text-center">
                                        <div className="text-xs text-muted-foreground mb-1">True Negative</div>
                                        <div className="text-2xl font-mono font-bold text-accent">
                                          {result.confusion_matrix.true_negative}
                                        </div>
                                      </div>
                                      <div className="p-3 rounded-md bg-destructive/10 border border-destructive/20 text-center">
                                        <div className="text-xs text-muted-foreground mb-1">False Positive</div>
                                        <div className="text-2xl font-mono font-bold text-destructive">
                                          {result.confusion_matrix.false_positive}
                                        </div>
                                      </div>
                                      <div className="p-3 rounded-md bg-destructive/10 border border-destructive/20 text-center">
                                        <div className="text-xs text-muted-foreground mb-1">False Negative</div>
                                        <div className="text-2xl font-mono font-bold text-destructive">
                                          {result.confusion_matrix.false_negative}
                                        </div>
                                      </div>
                                      <div className="p-3 rounded-md bg-accent/10 border border-accent/20 text-center">
                                        <div className="text-xs text-muted-foreground mb-1">True Positive</div>
                                        <div className="text-2xl font-mono font-bold text-accent">
                                          {result.confusion_matrix.true_positive}
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-muted-foreground text-center py-8">No ML results available yet</p>
                      )}
                    </div>
                  </TabsContent>

                  <TabsContent value="chat" data-testid="chat-content">
                    <div className="space-y-4">
                      <div className="h-[400px] overflow-y-auto border border-border rounded-md p-4 space-y-3 bg-secondary">
                        {chatHistory.length === 0 ? (
                          <p className="text-sm text-muted-foreground text-center py-8">
                            Ask questions about your analysis results
                          </p>
                        ) : (
                          chatHistory.map((msg, idx) => (
                            <div
                              key={idx}
                              className={`p-3 rounded-md ${
                                msg.role === 'user'
                                  ? 'bg-primary/10 ml-12 border border-primary/20'
                                  : 'bg-card mr-12 border border-border'
                              }`}
                            >
                              <div className="metric-label mb-1">
                                {msg.role === 'user' ? 'You' : 'AI Assistant'}
                              </div>
                              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
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
                        />
                        <Button onClick={handleChat} data-testid="chat-send-button">
                          <MessageSquare className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </TabsContent>
                </Tabs>
              </Card>
            ) : (
              <Card className="p-12 data-card text-center">
                <Activity className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-xl font-semibold mb-2">No Active Analysis</h3>
                <p className="text-muted-foreground">Upload files, enter a project name, and start an analysis to see results</p>
              </Card>
            )}
          </div>
        </div>

        {/* Recent Analyses */}
        {analyses.length > 0 && (
          <Card className="p-6 data-card">
            <h3 className="text-lg font-semibold mb-4">Recent Analyses</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {analyses.slice(0, 6).map(analysis => (
                <div
                  key={analysis.id}
                  className="p-4 rounded-md border border-border hover:border-primary/50 cursor-pointer transition-colors bg-secondary"
                  onClick={() => loadAnalysis(analysis.id)}
                  data-testid={`analysis-${analysis.id}`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium truncate">{analysis.project_name}</h4>
                      <span className="text-xs text-muted-foreground">
                        {new Date(analysis.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`status-badge ${
                        analysis.status === 'completed' ? 'bg-accent/20 text-accent' : 
                        analysis.status === 'processing' ? 'bg-primary/20 text-primary' :
                        'bg-destructive/20 text-destructive'
                      }`}>
                        {analysis.status}
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => handleDeleteAnalysis(analysis.id, e)}
                        className="h-6 w-6 p-0"
                        data-testid={`delete-analysis-${analysis.id}`}
                      >
                        <Trash2 className="w-4 h-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                  {analysis.progress < 100 && (
                    <Progress value={analysis.progress} className="h-1 mt-2" />
                  )}
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </DashboardLayout>
  );
}
