import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Crown, Save, Check, HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const DEFAULT_PRESETS = [
    {
        id: 'full-council',
        name: 'Full Council',
        description: 'All members present for a balanced perspective.',
        framework: 'standard',
        councilModels: [], // Empty implies all default
        chairmanModel: 'google/gemini-pro'
    },
    {
        id: 'dev-squad',
        name: 'Dev Squad',
        description: 'Technical focus with Codex leading.',
        framework: 'standard',
        councilModels: ['anthropic/claude-3-sonnet', 'openai/gpt-4-turbo'],
        chairmanModel: 'anthropic/claude-3-sonnet'
    },
    {
        id: 'creative-spark',
        name: 'Creative Spark',
        description: 'Brainstorming session with Luna.',
        framework: 'six_hats',
        councilModels: ['google/gemini-pro', 'openai/gpt-4o'],
        chairmanModel: 'google/gemini-pro'
    }
];

const CouncilConfigDialog = ({
    open,
    onOpenChange,
    models,
    selectedFramework,
    setSelectedFramework,
    councilModels,
    setCouncilModels,
    chairmanModel,
    setChairmanModel,
    presets,
    onSavePreset
}) => {
    // Merge default and user presets
    const allPresets = [...DEFAULT_PRESETS, ...presets];
    const [activePresetId, setActivePresetId] = useState(null);

    // Apply preset logic
    const applyPreset = (preset) => {
        setActivePresetId(preset.id);
        setSelectedFramework(preset.framework || 'standard');
        setChairmanModel(preset.chairmanModel || '');
        setCouncilModels(preset.councilModels || []);
    };

    // Toggle model in council (max 5)
    const toggleModel = (modelId) => {
        setActivePresetId(null); // Customizing breaks preset link
        if (councilModels.includes(modelId)) {
            setCouncilModels(councilModels.filter(id => id !== modelId));
            if (chairmanModel === modelId) setChairmanModel(''); // Remove chair if removed from council? Optional logic.
        } else {
            if (councilModels.length >= 5) return; // Max 5 limits
            setCouncilModels([...councilModels, modelId]);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col p-0 gap-0">
                <DialogHeader className="p-6 pb-2">
                    <DialogTitle className="text-xl">Council Configuration</DialogTitle>
                    <DialogDescription>
                        Select active agents, appoint a chairman, or load a preset configuration.
                    </DialogDescription>
                </DialogHeader>

                <ScrollArea className="flex-1 px-6 py-2">
                    <div className="space-y-6 pb-6">

                        {/* 1. Presets */}
                        <div className="space-y-3">
                            <h3 className="text-sm font-semibold text-muted-foreground">Council Types (Presets)</h3>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {allPresets.map(preset => (
                                    <Card
                                        key={preset.id}
                                        className={cn(
                                            "cursor-pointer hover:bg-accent/50 transition-colors relative",
                                            activePresetId === preset.id ? "border-primary bg-accent/20" : ""
                                        )}
                                        onClick={() => applyPreset(preset)}
                                    >
                                        <CardContent className="p-4">
                                            <div className="flex justify-between items-start mb-2">
                                                <div className="font-semibold text-sm">{preset.name}</div>
                                                {activePresetId === preset.id && <Check className="h-4 w-4 text-primary" />}
                                            </div>
                                            <p className="text-xs text-muted-foreground line-clamp-2">
                                                {preset.description}
                                            </p>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        </div>

                        {/* 2. Council Members */}
                        <div className="space-y-3">
                            <div className="flex items-center justify-between">
                                <h3 className="text-sm font-semibold text-muted-foreground">Council Members</h3>
                                <div className="text-xs text-muted-foreground">{councilModels.length} Active</div>
                            </div>

                            <div className="rounded-md border bg-card">
                                {models.map((model) => {
                                    const isActive = councilModels.includes(model.id);
                                    const isChairman = chairmanModel === model.id;

                                    return (
                                        <div key={model.id} className="flex items-center justify-between p-3 border-b last:border-0 hover:bg-muted/30 transition-colors">
                                            <div className="flex items-center gap-3">
                                                <Switch
                                                    checked={isActive}
                                                    onCheckedChange={() => toggleModel(model.id)}
                                                />
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-medium flex items-center gap-2">
                                                        {model.name}
                                                        {isChairman && <Badge variant="default" className="bg-amber-500 hover:bg-amber-600 text-white h-5 px-1.5 gap-0.5"><Crown className="h-3 w-3" /> Chairman</Badge>}
                                                    </span>
                                                    <span className="text-xs text-muted-foreground">{model.id}</span>
                                                </div>
                                            </div>

                                            {isActive && !isChairman && (
                                                <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => {
                                                    setChairmanModel(model.id);
                                                    setActivePresetId(null);
                                                }}>
                                                    Appoint Chair
                                                </Button>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        {/* 3. Chairman Selector & Framework (Legacy/Fallback controls) */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-3">
                                <h3 className="text-sm font-semibold text-muted-foreground">Council Chairman</h3>
                                <Select value={chairmanModel} onValueChange={(val) => { setChairmanModel(val); setActivePresetId(null); }}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select Chairman" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {models.filter(m => councilModels.includes(m.id)).map(m => (
                                            <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                                <p className="text-xs text-muted-foreground">
                                    The Chairman leads the conversation and synthesizes responses from other members.
                                </p>
                            </div>

                            <div className="space-y-3">
                                <div className="flex items-center gap-2">
                                    <h3 className="text-sm font-semibold text-muted-foreground">Framework</h3>
                                    <Popover>
                                        <PopoverTrigger asChild>
                                            <Button variant="ghost" size="icon" className="h-4 w-4 text-muted-foreground hover:text-primary">
                                                <HelpCircle className="h-3 w-3" />
                                            </Button>
                                        </PopoverTrigger>
                                        <PopoverContent className="w-80 p-4">
                                            <div className="space-y-2">
                                                <h4 className="font-semibold text-sm">Council Frameworks</h4>
                                                <ul className="text-xs space-y-2 text-muted-foreground">
                                                    <li><strong>Standard:</strong> Models give individual answers, then rank each other. Chairman synthesizes.</li>
                                                    <li><strong>Debate:</strong> Models critique each other's responses. Chairman finds the truth.</li>
                                                    <li><strong>Six Hats:</strong> Models adopt specific perspectives (optimist, critic, etc.). Great for brainstorming.</li>
                                                    <li><strong>Ensemble:</strong> Fast parallel responses synthesized by Chairman. No ranking stage.</li>
                                                </ul>
                                            </div>
                                        </PopoverContent>
                                    </Popover>
                                </div>
                                <Select value={selectedFramework} onValueChange={(val) => { setSelectedFramework(val); setActivePresetId(null); }}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select Framework" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="standard">Standard Council</SelectItem>
                                        <SelectItem value="debate">Chain of Debate</SelectItem>
                                        <SelectItem value="six_hats">Six Thinking Hats</SelectItem>
                                        <SelectItem value="ensemble">Ensemble (Fast)</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>

                    </div>
                </ScrollArea>

                <DialogFooter className="p-4 border-t bg-muted/20 flex sm:justify-between items-center">
                    <Button variant="outline" className="w-full sm:w-auto" onClick={onSavePreset}>
                        <Save className="mr-2 h-4 w-4" />
                        Save Current Config as Type
                    </Button>
                    <Button onClick={() => onOpenChange(false)} className="w-full sm:w-auto">
                        Done
                    </Button>
                </DialogFooter>

            </DialogContent>
        </Dialog>
    );
};

export default CouncilConfigDialog;
