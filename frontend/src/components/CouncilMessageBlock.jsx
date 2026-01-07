
import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AlertTriangle, Trophy, Crown, User, BrainCircuit } from "lucide-react";
import { cn } from "@/lib/utils";

const MarkdownContent = ({ content }) => (
    <div className="prose prose-sm dark:prose-invert max-w-none break-words">
        <ReactMarkdown>{content}</ReactMarkdown>
    </div>
);

const CouncilMessageBlock = ({ message }) => {
    const { stage1, stage2, stage3, loading, errors, metadata } = message;
    const [activeTab, setActiveTab] = useState("consensus");

    // Determine stage progress
    const hasStage1 = stage1 && stage1.length > 0;
    const hasStage2 = stage2 && stage2.length > 0;
    const hasStage3 = stage3 && stage3.response;

    // Create tabs list
    // Default: Consensus (if Stage 3 started or complete)
    // Then: Rankings (if Stage 2 present)
    // Then: Individual Models (Stage 1)

    // If only stage 1 is running, default to first model or "thinking"
    useEffect(() => {
        if (hasStage3) {
            setActiveTab("consensus");
        } else if (hasStage1 && !hasStage3 && activeTab === 'consensus') {
            // If stage 3 not started but stage 1 has items, maybe show first model?
            // Or keep 'consensus' as a placeholder for "Thinking..."
        }
    }, [hasStage3, hasStage1]);

    const aggregateRankings = metadata?.aggregate_rankings || [];

    return (
        <Card className="w-full border-2 border-transparent data-[state=chairman]:border-chairman/20 overflow-hidden">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <div className="bg-muted/50 border-b px-4 py-2 flex items-center justify-between flex-wrap gap-2">
                    <TabsList className="h-9 bg-background/50">
                        <TabsTrigger value="consensus" className="gap-2">
                            <Crown className="h-3.5 w-3.5 text-chairman" />
                            Consensus
                        </TabsTrigger>
                        {hasStage2 && (
                            <TabsTrigger value="rankings" className="gap-2">
                                <Trophy className="h-3.5 w-3.5 text-yellow-500" />
                                Rankings
                            </TabsTrigger>
                        )}
                        {hasStage1 && stage1.map((res, idx) => (
                            <TabsTrigger key={idx} value={`model-${idx}`} className="hidden sm:inline-flex">
                                {res.model.split('/')[1] || res.model}
                            </TabsTrigger>
                        ))}
                    </TabsList>

                    {/* Mobile Dropdown for models could go here if needed, or scroll tabs */}
                </div>

                <div className="p-0">
                    {/* Consensus Tab */}
                    <TabsContent value="consensus" className="m-0 focus-visible:ring-0">
                        <div className="p-6 min-h-[100px]">
                            {hasStage3 ? (
                                <>
                                    <div className="flex items-center gap-2 mb-4">
                                        <Badge variant="outline" className="border-chairman text-chairman gap-1">
                                            <Crown className="h-3 w-3" />
                                            Chairman: {stage3.model}
                                        </Badge>
                                        {metadata?.framework && (
                                            <Badge variant="secondary" className="text-xs">
                                                {metadata.framework}
                                            </Badge>
                                        )}
                                    </div>
                                    <MarkdownContent content={stage3.response} />
                                    {loading?.stage3 && <span className="inline-block w-2 h-4 bg-primary animate-pulse ml-1" />}
                                </>
                            ) : (
                                <div className="flex flex-col items-center justify-center p-8 text-muted-foreground gap-3">
                                    <BrainCircuit className="h-8 w-8 animate-pulse text-primary/50" />
                                    <p>The Council is deliberating...</p>
                                    <div className="flex gap-2 text-xs">
                                        <span className={cn("transition-opacity", loading?.stage1 ? "opacity-100 font-medium text-foreground" : "opacity-50")}>Collecting Thoughts</span>
                                        <span>→</span>
                                        <span className={cn("transition-opacity", loading?.stage2 ? "opacity-100 font-medium text-foreground" : "opacity-50")}>Debating</span>
                                        <span>→</span>
                                        <span className={cn("transition-opacity", loading?.stage3 ? "opacity-100 font-medium text-foreground" : "opacity-50")}>Synthesizing</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </TabsContent>

                    {/* Rankings Tab */}
                    <TabsContent value="rankings" className="m-0 focus-visible:ring-0">
                        <div className="p-6">
                            <h3 className="font-semibold mb-4">Council Rankings</h3>
                            <div className="space-y-4">
                                {aggregateRankings.length > 0 ? (
                                    aggregateRankings.map((rank, idx) => (
                                        <div key={idx} className="flex items-center justify-between p-3 border rounded-lg bg-card/50">
                                            <div className="flex items-center gap-3">
                                                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted font-bold">
                                                    {idx + 1}
                                                </div>
                                                <div>
                                                    <div className="font-medium">{rank.model}</div>
                                                    <div className="text-xs text-muted-foreground">{rank.rankings_count} evaluations</div>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <div className="font-mono font-bold text-lg">{rank.average_rank}</div>
                                                <div className="text-xs text-muted-foreground">Avg Rank</div>
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div className="text-muted-foreground italic">No rankings available for this session type.</div>
                                )}
                            </div>
                        </div>
                    </TabsContent>

                    {/* Individual Models Tabs */}
                    {hasStage1 && stage1.map((res, idx) => (
                        <TabsContent key={idx} value={`model-${idx}`} className="m-0 focus-visible:ring-0">
                            <div className="p-6">
                                <div className="flex items-center gap-2 mb-4">
                                    <Badge variant="outline">{res.model}</Badge>
                                </div>
                                <MarkdownContent content={res.response} />
                            </div>
                        </TabsContent>
                    ))}
                </div>

                {/* Errors Footer */}
                {errors && errors.length > 0 && (
                    <div className="bg-destructive/10 p-4 border-t border-destructive/20 text-destructive text-sm">
                        <div className="font-semibold flex items-center gap-2 mb-1">
                            <AlertTriangle className="h-4 w-4" />
                            Errors detected:
                        </div>
                        <ul className="list-disc list-inside">
                            {errors.map((err, idx) => (
                                <li key={idx}><strong>{err.model}:</strong> {err.error}</li>
                            ))}
                        </ul>
                    </div>
                )}
            </Tabs>
        </Card>
    );
};

export default CouncilMessageBlock;
