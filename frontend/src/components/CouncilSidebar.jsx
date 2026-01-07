
import React, { useState, useEffect, memo } from 'react';
import { api } from '../api';
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Trash2, Plus, History, Settings, PanelLeftClose, PanelLeftOpen, Users } from "lucide-react";
import CouncilConfigDialog from './CouncilConfigDialog';
import { cn } from "@/lib/utils";

const CouncilSidebar = memo(({
    conversations,
    currentConversationId,
    onSelectConversation,
    onNewConversation,
    isMobile,
    isOpen,
    onClose,
}) => {
    // Config State
    const [selectedFramework, setSelectedFramework] = useState('standard');
    const [models, setModels] = useState([]);
    const [chairmanModel, setChairmanModel] = useState('');
    const [councilModels, setCouncilModels] = useState([]);
    const [loadingModels, setLoadingModels] = useState(false);

    // Status & Presets
    const [status, setStatus] = useState(null);
    const [presets, setPresets] = useState([]);
    const [showConfigDialog, setShowConfigDialog] = useState(false);

    // Sidebar State
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [showAllHistory, setShowAllHistory] = useState(false);

    // Filter conversations
    const recentConversations = conversations.slice(0, 5);
    const olderConversations = conversations.slice(5);

    useEffect(() => {
        loadModels();
        loadStatus();
        loadPresets();
    }, []);

    const loadStatus = async () => {
        try {
            const s = await api.getStatus();
            setStatus(s);
        } catch (e) { console.error("Failed to load status", e); }
    };

    const loadModels = async () => {
        setLoadingModels(true);
        try {
            const data = await api.getModels();
            setModels(data);
            // Default chairman if empty
            if (data.length > 0 && !chairmanModel) {
                setChairmanModel(data[0].id);
            }
        } catch (error) {
            console.error("Failed to load models", error);
        } finally {
            setLoadingModels(false);
        }
    };

    const loadPresets = () => {
        const saved = localStorage.getItem('council_presets');
        if (saved) {
            try {
                setPresets(JSON.parse(saved));
            } catch (e) { console.error("Failed to parse presets", e); }
        }
    };

    const handleSavePreset = () => {
        // This is now triggered from within the Dialog mostly, but if we need a direct save:
        // Identify name? The dialog handles the logic now. We just pass the callback.
    };

    const saveNewPreset = (name) => {
        const newPreset = {
            id: Date.now().toString(),
            name: name,
            description: `Custom preset created on ${new Date().toLocaleDateString()}`,
            framework: selectedFramework,
            chairmanModel,
            councilModels
        };
        const updated = [...presets, newPreset];
        setPresets(updated);
        localStorage.setItem('council_presets', JSON.stringify(updated));
    };

    const handleNewChat = () => {
        onNewConversation(selectedFramework, councilModels, chairmanModel);
        if (isMobile) onClose();
    };

    const handleDelete = async (e, id) => {
        e.stopPropagation();
        if (!confirm("Delete this conversation?")) return;
        try {
            await api.deleteConversation(id);
            // Parent should reload or we wait for prop update
            window.location.reload(); // Temporary fix for state sync
        } catch (err) {
            alert("Failed to delete conversation");
        }
    };

    // Derived state for display
    const activeChairmanName = models.find(m => m.id === chairmanModel)?.name || "Auto";
    const activeMemberCount = councilModels.length || "All";

    return (
        <>
            <div className={cn(
                "fixed inset-y-0 left-0 z-50 transform border-r bg-background transition-all duration-300 ease-in-out flex flex-col",
                isOpen ? "translate-x-0" : "-translate-x-full",
                "md:relative md:translate-x-0",
                isCollapsed ? "w-16" : "w-80"
            )}>
                {/* Header */}
                <div className={cn("p-4 border-b flex items-center", isCollapsed ? "justify-center" : "justify-between")}>
                    {!isCollapsed && (
                        <div className="flex items-center gap-2 overflow-hidden">
                            <div className="h-8 w-8 rounded bg-primary text-primary-foreground flex items-center justify-center font-bold text-lg">
                                L
                            </div>
                            <div className="truncate">
                                <h2 className="font-bold tracking-tight text-sm">LLM Council</h2>
                                <p className="text-xs text-muted-foreground">AI Workspace</p>
                            </div>
                        </div>
                    )}
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setIsCollapsed(!isCollapsed)}
                        className="h-8 w-8 ml-auto"
                        title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
                    >
                        {isCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
                    </Button>
                </div>

                {/* Actions */}
                <div className="p-3">
                    <Button
                        className={cn("w-full justify-start", isCollapsed && "justify-center px-0")}
                        onClick={handleNewChat}
                        variant={isCollapsed ? "outline" : "default"}
                    >
                        <Plus className={cn("h-4 w-4", !isCollapsed && "mr-2")} />
                        {!isCollapsed && "New Session"}
                    </Button>
                </div>

                <Separator />

                <ScrollArea className="flex-1">
                    <div className="p-3 space-y-6">
                        {/* Council Config Trigger */}
                        <div className="space-y-2">
                            {!isCollapsed && (
                                <h3 className="text-xs font-semibold text-muted-foreground px-2">
                                    Council Members
                                </h3>
                            )}
                            <Button
                                variant="outline"
                                className={cn("w-full justify-start relative", isCollapsed && "justify-center px-0 h-10")}
                                onClick={() => setShowConfigDialog(true)}
                            >
                                <Users className={cn("h-4 w-4", !isCollapsed && "mr-2")} />
                                {!isCollapsed && (
                                    <div className="flex flex-col items-start text-xs truncate">
                                        <span>Manage Council</span>
                                        <span className="font-normal text-muted-foreground text-[10px]">
                                            {activeMemberCount} Members • {activeChairmanName}
                                        </span>
                                    </div>
                                )}
                            </Button>
                        </div>

                        {/* Recent History */}
                        <div className="space-y-1">
                            {!isCollapsed && (
                                <h3 className="text-xs font-semibold text-muted-foreground px-2 flex items-center mb-2">
                                    Recent Sessions
                                </h3>
                            )}

                            {/* Render History Items */}
                            {recentConversations.map(conv => (
                                <TooltipProvider key={conv.id} delayDuration={0}>
                                    <Tooltip>
                                        <TooltipTrigger asChild>
                                            <div
                                                className={cn(
                                                    "group flex items-center rounded-md px-2 py-2 text-sm hover:bg-accent/50 cursor-pointer relative",
                                                    currentConversationId === conv.id ? 'bg-accent text-accent-foreground font-medium' : '',
                                                    isCollapsed ? "justify-center" : "justify-between"
                                                )}
                                                onClick={() => onSelectConversation(conv.id)}
                                            >
                                                {isCollapsed ? (
                                                    <History className="h-4 w-4 text-muted-foreground" />
                                                ) : (
                                                    <div className="flex items-center gap-2 truncate pr-6 w-full">
                                                        <History className="h-4 w-4 text-muted-foreground shrink-0" />
                                                        <span className="truncate">{conv.title}</span>
                                                    </div>
                                                )}

                                                {/* Delete Button - Fixed Visibility */}
                                                {!isCollapsed && (
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        className="h-6 w-6 absolute right-1 opacity-50 group-hover:opacity-100 transition-opacity hover:bg-destructive/10 hover:text-destructive"
                                                        onClick={(e) => handleDelete(e, conv.id)}
                                                    >
                                                        <Trash2 className="h-3 w-3" />
                                                    </Button>
                                                )}
                                            </div>
                                        </TooltipTrigger>
                                        {isCollapsed && <TooltipContent side="right">{conv.title}</TooltipContent>}
                                    </Tooltip>
                                </TooltipProvider>
                            ))}
                        </div>
                    </div>
                </ScrollArea>

                {/* Settings Footer */}
                <div className="p-3 border-t">
                    <Button
                        variant="ghost"
                        size="sm"
                        className={cn("w-full justify-start", isCollapsed && "justify-center px-0")}
                    >
                        <Settings className={cn("h-4 w-4", !isCollapsed && "mr-2")} />
                        {!isCollapsed && "Settings"}
                    </Button>
                </div>
            </div>

            {/* Config Dialog */}
            <CouncilConfigDialog
                open={showConfigDialog}
                onOpenChange={setShowConfigDialog}
                models={models}
                selectedFramework={selectedFramework}
                setSelectedFramework={setSelectedFramework}
                councilModels={councilModels}
                setCouncilModels={setCouncilModels}
                chairmanModel={chairmanModel}
                setChairmanModel={setChairmanModel}
                presets={presets}
                onSavePreset={() => {
                    // Prompt for name in the dialog is managed inside? 
                    // Wait, the dialog I wrote triggers onSave which triggers logic.
                    // The dialog has its own prompt? No, I implemented "Save Current Config" button which likely needs to open a prompt or the dialog handles it.
                    // Let's check CouncilConfigDialog again. It has a button "Save Current Config as Type" which calls onSavePreset.
                    // It does NOT have a prompt inside. I should move the prompt logic inside CouncilConfigDialog or handle it here via a secondary dialog/prompt.
                    const name = prompt("Enter a name for this preset:");
                    if (name) saveNewPreset(name);
                }}
            />
        </>
    );
});

export default CouncilSidebar;

