import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
      <div className="max-w-4xl w-full px-4 text-center">
        <h1 className="text-5xl font-extrabold text-gray-900 mb-6 tracking-tight">
          DataForge SaaS
        </h1>
        <p className="text-xl text-gray-600 mb-10 max-w-2xl mx-auto">
          The generic, domain-agnostic AI data pipeline engine. Orchestrate complex data ingestion, structured extraction, quality assurance, and vectorization tasks with ease.
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/login">
            <Button size="lg" className="px-8 font-semibold">Login</Button>
          </Link>
          <Link href="/dashboard">
            <Button size="lg" variant="outline" className="px-8 font-semibold">Go to Dashboard</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
