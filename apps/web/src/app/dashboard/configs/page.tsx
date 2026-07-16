"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, Settings2 } from "lucide-react";

interface PipelineConfig {
  id: string;
  name: string;
  description: string | null;
  config_json: any;
}

export default function ConfigsPage() {
  const router = useRouter();
  const [configs, setConfigs] = useState<PipelineConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newConfigName, setNewConfigName] = useState("");
  const [newConfigDesc, setNewConfigDesc] = useState("");
  const [newConfigJson, setNewConfigJson] = useState("{\n  \"version\": \"1.0.0\",\n  \"input_type\": \"url\",\n  \"extraction\": {},\n  \"qa_rules\": [],\n  \"vectorization\": null\n}");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [jsonError, setJsonError] = useState("");

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    try {
      setLoading(true);
      const data = await fetchAPI("/configs");
      setConfigs(data);
    } catch (err) {
      console.error("Failed to load configs:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    setJsonError("");
    
    let parsedJson;
    try {
      parsedJson = JSON.parse(newConfigJson);
    } catch (err) {
      setJsonError("Invalid JSON format");
      return;
    }

    if (!newConfigName) return;
    
    setIsSubmitting(true);
    try {
      await fetchAPI("/configs", {
        method: "POST",
        body: JSON.stringify({
          name: newConfigName,
          description: newConfigDesc,
          config_json: parsedJson
        }),
      });
      setIsModalOpen(false);
      setNewConfigName("");
      setNewConfigDesc("");
      setNewConfigJson("{\n  \"version\": \"1.0.0\",\n  \"input_type\": \"url\",\n  \"extraction\": {},\n  \"qa_rules\": [],\n  \"vectorization\": null\n}");
      await loadConfigs();
    } catch (err) {
      console.error("Failed to create config:", err);
      alert("Failed to create config. See console.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) return <div className="p-8 text-center">Loading configurations...</div>;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <div className="flex items-center space-x-4 mb-4">
        <Button variant="ghost" onClick={() => router.push("/dashboard")} className="mb-1">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-3xl font-bold tracking-tight">Pipeline Configurations</h1>
      </div>

      <div className="flex justify-between items-center">
        <p className="text-muted-foreground">Manage your database-backed pipeline configurations.</p>
        <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
          <DialogTrigger asChild>
            <Button><Settings2 className="mr-2 h-4 w-4" /> Create New Config</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>Create Pipeline Configuration</DialogTitle>
              <DialogDescription>
                Define the extraction schema and QA rules dynamically.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateConfig}>
              <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="name" className="text-right">Name</Label>
                  <Input id="name" value={newConfigName} onChange={(e) => setNewConfigName(e.target.value)} className="col-span-3" placeholder="e.g. custom_medical_papers" required />
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                  <Label htmlFor="desc" className="text-right">Description</Label>
                  <Input id="desc" value={newConfigDesc} onChange={(e) => setNewConfigDesc(e.target.value)} className="col-span-3" placeholder="Optional description" />
                </div>
                <div className="grid grid-cols-4 items-start gap-4">
                  <Label htmlFor="json" className="text-right pt-2">Config JSON</Label>
                  <div className="col-span-3">
                    <textarea 
                      id="json" 
                      value={newConfigJson} 
                      onChange={(e) => setNewConfigJson(e.target.value)} 
                      className="flex min-h-[250px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 font-mono" 
                      required 
                    />
                    {jsonError && <p className="text-red-500 text-xs mt-1">{jsonError}</p>}
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Saving..." : "Save Config"}</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Available Configurations</CardTitle>
        </CardHeader>
        <CardContent>
          {configs.length === 0 ? (
            <div className="text-sm text-gray-500 py-4">No database configurations found. System will fallback to YAML files.</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Preview</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {configs.map((c) => (
                  <TableRow key={c.id}>
                    <TableCell className="font-semibold">{c.name}</TableCell>
                    <TableCell>{c.description || "-"}</TableCell>
                    <TableCell className="max-w-[300px]">
                      <pre className="text-xs truncate bg-muted p-1 rounded">
                        {JSON.stringify(c.config_json)}
                      </pre>
                    </TableCell>
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
