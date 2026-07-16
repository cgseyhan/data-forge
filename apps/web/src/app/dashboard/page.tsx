"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchAPI } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Settings2 } from "lucide-react";
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
  const [analytics, setAnalytics] = useState({ total_pipelines: 0, records_processed: 0, llm_tokens_used: 0 });
  const [loading, setLoading] = useState(true);
  const [isPipelineModalOpen, setIsPipelineModalOpen] = useState(false);
  const [newPipelineConfig, setNewPipelineConfig] = useState("legal_contracts");
  const [newPipelineSource, setNewPipelineSource] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [configs, setConfigs] = useState<any[]>([]);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    const loadData = async () => {
      try {
        const [recordsData, analyticsData, configsData] = await Promise.all([
          fetchAPI("/records"),
          fetchAPI("/analytics/summary"),
          fetchAPI("/configs").catch(() => []) // Fallback if configs fail
        ]);
        setRecords(recordsData);
        setAnalytics(analyticsData);
        setConfigs(configsData);
      } catch (err) {
        console.error("Failed to load data:", err);
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
      
      // Refresh data
      const [recordsData, analyticsData] = await Promise.all([
        fetchAPI("/records"),
        fetchAPI("/analytics/summary")
      ]);
      setRecords(recordsData);
      setAnalytics(analyticsData);
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
        <div className="flex space-x-2">
          <Button variant="outline" onClick={() => router.push("/dashboard/configs")}>
            <Settings2 className="mr-2 h-4 w-4" /> Manage Configs
          </Button>
          <Dialog open={isPipelineModalOpen} onOpenChange={setIsPipelineModalOpen}>
            <DialogTrigger asChild>
              <Button>Run Pipeline</Button>
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
                  <select
                    id="config"
                    value={newPipelineConfig}
                    onChange={(e) => setNewPipelineConfig(e.target.value)}
                    className="col-span-3 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    required
                  >
                    <option value="" disabled>Select a config...</option>
                    <option value="legal_contracts">legal_contracts (YAML)</option>
                    <option value="ecommerce_products">ecommerce_products (YAML)</option>
                    {configs.map(c => (
                      <option key={c.id} value={c.name}>{c.name} (DB)</option>
                    ))}
                  </select>
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
            <div className="text-2xl font-bold">{analytics.total_pipelines}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Records Processed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.records_processed}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">LLM Tokens Used</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{analytics.llm_tokens_used}</div>
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
