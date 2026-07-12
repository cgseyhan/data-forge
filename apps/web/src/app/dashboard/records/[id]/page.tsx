"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { fetchAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";

interface RecordDetail {
  id: string;
  source: string;
  pipeline_name: string;
  status: string;
  raw_content_preview: string | null;
  extracted_data: any;
  created_at: string;
  updated_at: string;
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
