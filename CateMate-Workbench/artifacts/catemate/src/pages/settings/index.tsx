import React, { useEffect, useState } from "react";
import { useGetSettings, useUpdateSettings } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Loader2 } from "lucide-react";

/** Backend provider id for Codex local proxy (OpenAI-compatible at 127.0.0.1). */
const PROVIDER_CODEX = "openai_compatible";
const PROVIDER_DEEPSEEK = "deepseek";

export default function Settings() {
  const { toast } = useToast();
  const { data: settings, isLoading } = useGetSettings();
  const updateSettings = useUpdateSettings();

  const [form, setForm] = useState({
    provider: PROVIDER_CODEX,
    model: "",
    baseUrl: "",
    apiKey: "",
    defaultPlanningMode: "v2_solve_loop",
    temperature: "",
    maxTokens: "",
    defaultTimeGranularity: "month",
  });

  useEffect(() => {
    if (settings) {
      setForm(prev => ({
        // UI default is Codex（本机代理）; user can switch to DeepSeek manually.
        provider: PROVIDER_CODEX,
        model: (settings as any).model || "",
        baseUrl: (settings as any).baseUrl || "",
        apiKey: prev.apiKey,
        defaultPlanningMode: (settings as any).defaultPlanningMode || "v2_solve_loop",
        temperature: (settings as any).temperature != null ? String((settings as any).temperature) : "",
        maxTokens: (settings as any).maxTokens != null ? String((settings as any).maxTokens) : "",
        defaultTimeGranularity: (settings as any).defaultTimeGranularity || "month",
      }));
    }
  }, [settings]);

  const isCodex = form.provider === PROVIDER_CODEX;
  const isDeepSeek = form.provider === PROVIDER_DEEPSEEK;

  const handleProviderChange = (value: string) => {
    setForm(p => ({ ...p, provider: value }));
  };

  const handleSave = () => {
    updateSettings.mutate(
      {
        data: {
          provider: form.provider || undefined,
          model: form.model || undefined,
          // Codex uses local proxy defaults on the backend; DeepSeek keeps existing baseUrl if any.
          baseUrl: isDeepSeek ? (form.baseUrl || undefined) : undefined,
          defaultPlanningMode: form.defaultPlanningMode || undefined,
          temperature: form.temperature ? parseFloat(form.temperature) : undefined,
          maxTokens: form.maxTokens ? parseInt(form.maxTokens) : undefined,
          defaultTimeGranularity: form.defaultTimeGranularity || undefined,
        } as any,
      },
      {
        onSuccess: () => toast({ title: "Settings saved" }),
        onError: () => toast({ title: "Failed to save settings", variant: "destructive" }),
      },
    );
  };

  if (isLoading) return <div className="p-8 animate-pulse text-muted-foreground">Loading settings...</div>;

  const enabledModules = (settings as any)?.enabledModules || [];

  return (
    <div className="p-8 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">System Settings</h1>
        <p className="text-muted-foreground mt-1">Configure AI providers and default behaviors.</p>
      </div>

      <Card className="bg-card">
        <CardHeader>
          <CardTitle>AI Provider</CardTitle>
          <CardDescription>Connection details for the reasoning engine.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Provider</Label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={form.provider}
                onChange={e => handleProviderChange(e.target.value)}
              >
                <option value={PROVIDER_CODEX}>Codex（本机代理）</option>
                <option value={PROVIDER_DEEPSEEK}>DeepSeek</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label>Model</Label>
              <Input value={form.model} onChange={e => setForm(p => ({ ...p, model: e.target.value }))} />
            </div>
          </div>

          {isCodex && (
            <div className="rounded-md border border-border bg-muted/40 px-3 py-3 text-sm text-muted-foreground">
              请确定已唤起 Codex Proxy
            </div>
          )}

          {isDeepSeek && (
            <div className="space-y-2">
              <Label>API Key</Label>
              <Input
                type="password"
                autoComplete="off"
                placeholder="DeepSeek API Key"
                value={form.apiKey}
                onChange={e => setForm(p => ({ ...p, apiKey: e.target.value }))}
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border mt-4">
            <div className="space-y-2">
              <Label>Temperature</Label>
              <Input type="number" step="0.1" value={form.temperature} onChange={e => setForm(p => ({ ...p, temperature: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>Max Tokens</Label>
              <Input type="number" value={form.maxTokens} onChange={e => setForm(p => ({ ...p, maxTokens: e.target.value }))} />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-card">
        <CardHeader>
          <CardTitle>Pipeline Defaults</CardTitle>
          <CardDescription>Default parameters for new analysis runs.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Default Planning Mode</Label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              value={form.defaultPlanningMode}
              onChange={e => setForm(p => ({ ...p, defaultPlanningMode: e.target.value }))}
            >
              <option value="v2_solve_loop">V2 Solve Loop</option>
              <option value="module_selection">Module Selection</option>
              <option value="ai_direct">AI Direct</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label>Default Time Granularity</Label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              value={form.defaultTimeGranularity}
              onChange={e => setForm(p => ({ ...p, defaultTimeGranularity: e.target.value }))}
            >
              <option value="month">Month</option>
              <option value="quarter">Quarter</option>
              <option value="year">Year</option>
            </select>
          </div>

          {enabledModules.length > 0 && (
            <div className="space-y-2 pt-4 border-t border-border">
              <Label>Enabled V2 Modules</Label>
              <div className="flex flex-wrap gap-2">
                {enabledModules.map((m: string) => (
                  <Badge key={m} variant="secondary">{m}</Badge>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                Module whitelist is managed in <code>config/output_grain_policy.yaml</code>.
              </p>
            </div>
          )}
        </CardContent>
        <CardFooter className="justify-end border-t border-border pt-4">
          <Button onClick={handleSave} disabled={updateSettings.isPending} className="gap-2">
            {updateSettings.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Settings
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
