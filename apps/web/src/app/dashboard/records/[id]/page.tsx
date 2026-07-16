"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { fetchAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, CheckCircle, XCircle, AlertCircle, Database } from "lucide-react";

interface QAResult {
  qa_type: string;
  status: string;
  score: number;
  issues_json: any;
}

interface VectorMeta {
  vector_backend: string;
  collection_name: string;
  embedding_model: string;
}

interface RecordDetail {
  id: string;
  source: string;
  pipeline_name: string;
  status: string;
  raw_content_preview: string | null;
  extracted_data: any;
  created_at: string;
  updated_at: string;
  qa_results: QAResult[];
  vector_metas: VectorMeta[];
}

export default function RecordDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [record, setRecord] = useState<RecordDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadRecord = async () => {
      try {
        const data = await fetchAPI(`/records/${id}`);
        setRecord(data);
      } catch (err: any) {
        console.error("Failed to load record:", err);
        setError(err.message || "Failed to load record");
      } finally {
        setLoading(false);
      }
    };
    if (id) loadRecord();
  }, [id]);

  if (loading) {
    return <div className="p-8 text-center">Loading record details...</div>;
  }

  if (error || !record) {
    return (
      <div className="p-8 max-w-7xl mx-auto space-y-4">
        <Button variant="ghost" onClick={() => router.push("/dashboard")}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Dashboard
        </Button>
        <div className="text-red-500">Error: {error || "Record not found"}</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex items-center space-x-4">
        <Button variant="ghost" onClick={() => router.push("/dashboard")} className="mb-1">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-3xl font-bold tracking-tight">Record Details</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Metadata</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div>
              <span className="font-semibold text-muted-foreground block">Record ID</span>
              <span className="break-all">{record.id}</span>
            </div>
            <div>
              <span className="font-semibold text-muted-foreground block">Pipeline</span>
              <span>{record.pipeline_name}</span>
            </div>
            <div>
              <span className="font-semibold text-muted-foreground block">Status</span>
              <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${
                record.status === 'QA_PASSED' ? 'bg-green-50 text-green-700 ring-green-600/20' : 
                record.status === 'QA_FAILED' ? 'bg-red-50 text-red-700 ring-red-600/10' :
                record.status === 'FAILED' ? 'bg-red-50 text-red-700 ring-red-600/10' :
                'bg-yellow-50 text-yellow-800 ring-yellow-600/20'
              }`}>
                {record.status}
              </span>
            </div>
            <div>
              <span className="font-semibold text-muted-foreground block">Source</span>
              <a href={record.source} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline break-all">
                {record.source}
              </a>
            </div>
            <div>
              <span className="font-semibold text-muted-foreground block">Created At</span>
              <span>{new Date(record.created_at).toLocaleString()}</span>
            </div>
          </CardContent>
        </Card>

        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Extracted Data</CardTitle>
              <CardDescription>Structured JSON output from the pipeline</CardDescription>
            </CardHeader>
            <CardContent>
              {record.extracted_data ? (
                <pre className="bg-muted/50 p-4 rounded-md overflow-x-auto text-sm">
                  {JSON.stringify(record.extracted_data, null, 2)}
                </pre>
              ) : (
                <div className="text-muted-foreground text-sm italic">No data extracted yet.</div>
              )}
            </CardContent>
          </Card>

          {/* QA Results Card */}
          <Card>
            <CardHeader>
              <CardTitle>Quality Assurance (QA) Results</CardTitle>
              <CardDescription>Automated rule and LLM judge validations</CardDescription>
            </CardHeader>
            <CardContent>
              {record.qa_results && record.qa_results.length > 0 ? (
                <div className="space-y-4">
                  {record.qa_results.map((qa, idx) => (
                    <div key={idx} className="flex flex-col space-y-2 p-4 border rounded-md">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          {qa.status === 'PASSED' ? (
                            <CheckCircle className="text-green-500 h-5 w-5" />
                          ) : qa.status === 'FAILED' ? (
                            <XCircle className="text-red-500 h-5 w-5" />
                          ) : (
                            <AlertCircle className="text-yellow-500 h-5 w-5" />
                          )}
                          <span className="font-semibold capitalize">{qa.qa_type.replace('_', ' ')}</span>
                        </div>
                        <span className={`text-xs font-bold px-2 py-1 rounded-md ${
                          qa.status === 'PASSED' ? 'bg-green-100 text-green-800' :
                          qa.status === 'FAILED' ? 'bg-red-100 text-red-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {qa.status}
                        </span>
                      </div>
                      
                      {qa.issues_json && Object.keys(qa.issues_json).length > 0 && (
                        <div className="mt-2 bg-red-50 text-red-800 p-3 rounded-md text-sm border border-red-100">
                          <span className="font-semibold block mb-1">Issues:</span>
                          <pre className="whitespace-pre-wrap">{JSON.stringify(qa.issues_json, null, 2)}</pre>
                        </div>
                      )}
                      {qa.score > 0 && (
                        <div className="text-sm text-muted-foreground">Score: {qa.score}</div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-muted-foreground text-sm italic">No QA rules executed for this record.</div>
              )}
            </CardContent>
          </Card>
          
          {/* Vector DB Card */}
          <Card>
            <CardHeader>
              <CardTitle>Vectorization Status</CardTitle>
              <CardDescription>Synchronization with vector databases</CardDescription>
            </CardHeader>
            <CardContent>
              {record.vector_metas && record.vector_metas.length > 0 ? (
                <div className="space-y-4">
                  {record.vector_metas.map((vm, idx) => (
                    <div key={idx} className="flex items-center p-4 border rounded-md justify-between bg-muted/20">
                      <div className="flex items-center space-x-3">
                        <Database className="h-5 w-5 text-blue-500" />
                        <div>
                          <span className="font-semibold block">{vm.vector_backend}</span>
                          <span className="text-xs text-muted-foreground block">Collection: {vm.collection_name}</span>
                        </div>
                      </div>
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-md font-semibold">
                        Model: {vm.embedding_model}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-muted-foreground text-sm italic">Record has not been vectorized yet.</div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Raw Content Preview</CardTitle>
            </CardHeader>
            <CardContent>
              {record.raw_content_preview ? (
                <pre className="bg-muted/50 p-4 rounded-md overflow-x-auto text-sm whitespace-pre-wrap">
                  {record.raw_content_preview}
                </pre>
              ) : (
                <div className="text-muted-foreground text-sm italic">No raw content available.</div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
