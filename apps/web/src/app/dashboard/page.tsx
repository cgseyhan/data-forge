"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchAPI } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface RecordItem {
  id: string;
  source: string;
  pipeline_name: string;
  status: string;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [isPipelineModalOpen, setIsPipelineModalOpen] = useState(false);
  const [newPipelineConfig, setNewPipelineConfig] = useState("legal_contracts");
  const [newPipelineSource, setNewPipelineSource] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    const loadData = async () => {
      try {
        const data = await fetchAPI("/records");
        setRecords(data);
      } catch (err) {
        console.error("Failed to load records:", err);
        // If unauthorized, redirect to login
        if (err instanceof Error && err.message === "Could not validate credentials") {
          localStorage.removeItem("token");
          router.push("/login");
        }
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [router]);

  const handleCreatePipeline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPipelineConfig || !newPipelineSource) return;
    
    setIsSubmitting(true);
    try {
      await fetchAPI(`/pipelines/${newPipelineConfig}/run`, {
        method: "POST",
        body: JSON.stringify({ source: newPipelineSource }),
      });
      setIsPipelineModalOpen(false);
      setNewPipelineSource("");
      
      // Refresh records
      const data = await fetchAPI("/records");
      setRecords(data);
    } catch (err) {
      console.error("Failed to start pipeline:", err);
      alert("Failed to start pipeline. See console for details.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center">Loading dashboard...</div>;
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <Dialog open={isPipelineModalOpen} onOpenChange={setIsPipelineModalOpen}>
          <DialogTrigger asChild>
            <Button>Create New Pipeline</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Run Pipeline</DialogTitle>
              <DialogDescription>
                Trigger a new ingestion and extraction pipeline run.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreatePipeline}>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="config" className="text-right">
                    Config Name
                  </Label>
                  <Input
                    id="config"
                    value={newPipelineConfig}
                    onChange={(e) => setNewPipelineConfig(e.target.value)}
                    className="col-span-3"
                    placeholder="e.g. legal_contracts"
                  />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="source" className="text-right">
                    Source
                  </Label>
                  <Input
                    id="source"
                    value={newPipelineSource}
                    onChange={(e) => setNewPipelineSource(e.target.value)}
                    className="col-span-3"
                    placeholder="URL or raw text"
                  />
                </div>
              </div>
              <DialogFooter>
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? "Starting..." : "Run Pipeline"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Pipelines</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Records Processed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{records.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">LLM Tokens Used</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Records</CardTitle>
          <CardDescription>A list of recently processed records across your pipelines.</CardDescription>
        </CardHeader>
        <CardContent>
          {records.length === 0 ? (
            <div className="text-sm text-gray-500 py-4">No records found. Run a pipeline to see results here.</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Record ID</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Pipeline</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {records.map((r) => (
                  <TableRow 
                    key={r.id}
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => router.push(`/dashboard/records/${r.id}`)}
                  >
                    <TableCell className="font-medium text-xs">{r.id.split('-')[0]}...</TableCell>
                    <TableCell className="truncate max-w-[200px]">{r.source}</TableCell>
                    <TableCell>{r.pipeline_name}</TableCell>
                    <TableCell>
                      <span className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${
                        r.status === 'QA_PASSED' ? 'bg-green-50 text-green-700 ring-green-600/20' : 
                        r.status === 'QA_FAILED' ? 'bg-red-50 text-red-700 ring-red-600/10' :
                        r.status === 'FAILED' ? 'bg-red-50 text-red-700 ring-red-600/10' :
                        'bg-yellow-50 text-yellow-800 ring-yellow-600/20'
                      }`}>
                        {r.status}
                      </span>
                    </TableCell>
                    <TableCell>{new Date(r.created_at).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
