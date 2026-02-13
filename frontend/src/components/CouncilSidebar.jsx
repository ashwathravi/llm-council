import { useState, useEffect, memo } from 'react';
import { api } from '../api';
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Trash2, Plus, History, Settings, PanelLeftClose, PanelLeftOpen, Users } from "lucide-react";
import CouncilConfigDialog from './CouncilConfigDialog';
import { cn } from "@/lib/utils";

const FRAMEWORK_LABELS = {
  standard: 'Standard Council',
  debate: 'Chain of Debate',
  six_hats: 'Six Thinking Hats',
  ensemble: 'Ensemble (Fast)',
};

const clampSelectionLimit = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 5;
  return Math.max(1, Math.min(10, Math.floor(parsed)));
};

const readSavedPresets = () => {
  const savedPresets = localStorage.getItem('council_presets');
  if (!savedPresets) return [];
  try {
    const parsed = JSON.parse(savedPresets);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.error('Failed to parse presets', error);
    return [];
  }
};

const readFavoriteModels = () => {
  const savedFavorites = localStorage.getItem('favorite_models');
  if (!savedFavorites) return [];
  try {
    const parsed = JSON.parse(savedFavorites);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((id) => typeof id === 'string');
  } catch (error) {
    console.error('Failed to parse favorite models', error);
    return [];
  }
};

const readMaxCouncilModels = () => {
  const savedMax = localStorage.getItem('council_max_models');
  return savedMax ? clampSelectionLimit(savedMax) : 5;
};

const normalizeModelList = (models) => {
  if (!Array.isArray(models)) return [];
  return [...new Set(models)].sort();
};

const sameConfig = (left, right) => {
  const leftModels = normalizeModelList(left.councilModels);
  const rightModels = normalizeModelList(right.councilModels);

  if (left.framework !== right.framework) return false;
  if ((left.chairmanModel || '') !== (right.chairmanModel || '')) return false;
  if (leftModels.length !== rightModels.length) return false;

  return leftModels.every((modelId, index) => modelId === rightModels[index]);
};

const CouncilSidebar = memo(({
  conversations,
  currentConversation,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  isMobile,
  isOpen,
  onClose,
}) => {
  const [selectedFramework, setSelectedFramework] = useState('standard');
  const [models, setModels] = useState([]);
  const [chairmanModel, setChairmanModel] = useState('');
  const [councilModels, setCouncilModels] = useState([]);

  const [presets, setPresets] = useState(readSavedPresets);
  const [favoriteModels, setFavoriteModels] = useState(readFavoriteModels);
  const [maxCouncilModels, setMaxCouncilModels] = useState(readMaxCouncilModels);

  const [showConfigDialog, setShowConfigDialog] = useState(false);
  const [configDialogView, setConfigDialogView] = useState('new_config');
  const [configDialogMode, setConfigDialogMode] = useState('create');
  const [isCreatingSession, setIsCreatingSession] = useState(false);

  const [isCollapsed, setIsCollapsed] = useState(false);

  const recentConversations = conversations.slice(0, 5);

  useEffect(() => {
    const loadModels = async () => {
      try {
        const data = await api.getModels();
        setModels(data);

        const availableModelIds = new Set(data.map((model) => model.id));

        setFavoriteModels((currentFavorites) =>
          currentFavorites.filter((modelId) => availableModelIds.has(modelId))
        );

        setChairmanModel((currentChairman) => {
          if (!currentChairman) return '';
          return availableModelIds.has(currentChairman) ? currentChairman : '';
        });

        setCouncilModels((currentCouncilModels) =>
          currentCouncilModels
            .filter((modelId) => availableModelIds.has(modelId))
        );
      } catch (error) {
        console.error('Failed to load models', error);
      }
    };

    loadModels();
  }, []);

  useEffect(() => {
    localStorage.setItem('favorite_models', JSON.stringify(favoriteModels));
  }, [favoriteModels]);

  useEffect(() => {
    localStorage.setItem('council_max_models', String(maxCouncilModels));
  }, [maxCouncilModels]);

  const getModelName = (modelId) => models.find((model) => model.id === modelId)?.name || modelId;

  const buildDefaultPresetName = () => {
    const councilTypeName = FRAMEWORK_LABELS[selectedFramework] || selectedFramework;
    const memberCount = councilModels.length;
    const chairmanName = models.find((model) => model.id === chairmanModel)?.name || chairmanModel;

    if (chairmanModel) {
      return `${councilTypeName} - ${memberCount} members - ${chairmanName}`;
    }

    return `${councilTypeName} - ${memberCount} members`;
  };

  const saveNewPreset = () => {
    const configToSave = {
      framework: selectedFramework,
      councilModels,
      chairmanModel,
    };

    const alreadySaved = presets.some((preset) => sameConfig(preset, configToSave));
    if (alreadySaved) {
      alert('This configuration is already saved.');
      return;
    }

    const defaultName = buildDefaultPresetName();
    const proposedName = prompt('Enter a name for this config:', defaultName);
    if (proposedName === null) return;

    const name = proposedName.trim() || defaultName;

    const newPreset = {
      id: Date.now().toString(),
      name,
      description: `Saved on ${new Date().toLocaleDateString()}`,
      framework: selectedFramework,
      chairmanModel,
      councilModels,
    };

    const updatedPresets = [...presets, newPreset];
    setPresets(updatedPresets);
    localStorage.setItem('council_presets', JSON.stringify(updatedPresets));
  };

  const handleMaxCouncilModelsChange = (nextMaxValue) => {
    const normalizedMax = clampSelectionLimit(nextMaxValue);
    setMaxCouncilModels(normalizedMax);

    if (councilModels.length <= normalizedMax) {
      return;
    }

    let trimmedCouncilModels = councilModels.slice(0, normalizedMax);
    const chairmanWasSelected = chairmanModel ? councilModels.includes(chairmanModel) : false;

    if (chairmanWasSelected && chairmanModel && !trimmedCouncilModels.includes(chairmanModel) && normalizedMax > 0) {
      trimmedCouncilModels = [
        ...trimmedCouncilModels.slice(0, normalizedMax - 1),
        chairmanModel,
      ];
    }

    let nextChairmanModel = chairmanModel;
    if (chairmanWasSelected && nextChairmanModel && !trimmedCouncilModels.includes(nextChairmanModel)) {
      nextChairmanModel = trimmedCouncilModels[0] || '';
    }

    setCouncilModels(trimmedCouncilModels);
    setChairmanModel(nextChairmanModel);
  };

  const openCreateConfigDialog = (view) => {
    setConfigDialogMode('create');
    setConfigDialogView(view);
    setShowConfigDialog(true);
  };

  const openReadOnlyDialog = () => {
    if (!currentConversation) return;
    setConfigDialogMode('read_only');
    setShowConfigDialog(true);
  };

  const handleDialogOpenChange = (open) => {
    setShowConfigDialog(open);
    if (!open) {
      setIsCreatingSession(false);
    }
  };

  const handleStartSession = async () => {
    setIsCreatingSession(true);
    try {
      await onNewConversation(selectedFramework, councilModels, chairmanModel || null);
      setShowConfigDialog(false);
      if (isMobile) onClose();
    } catch (error) {
      console.error('Failed to create conversation', error);
      alert('Failed to start a new session. Please try again.');
    } finally {
      setIsCreatingSession(false);
    }
  };

  const handleDelete = async (event, id) => {
    event.stopPropagation();
    if (!confirm('Delete this conversation?')) return;
    try {
      await api.deleteConversation(id);
      window.location.reload();
    } catch {
      alert('Failed to delete conversation');
    }
  };

  const activeConversationFramework = currentConversation?.framework;
  const activeFrameworkLabel = activeConversationFramework
    ? (FRAMEWORK_LABELS[activeConversationFramework] || activeConversationFramework)
    : 'No active conversation';
  const activeConversationModels = Array.isArray(currentConversation?.council_models)
    ? currentConversation.council_models
    : [];
  const activeConversationChairman = currentConversation?.chairman_model || '';
  const activeChairmanName = activeConversationChairman ? getModelName(activeConversationChairman) : 'Auto';

  return (
    <>
      <div
        className={cn(
          'fixed inset-y-0 left-0 z-50 transform border-r bg-background transition-all duration-300 ease-in-out flex flex-col',
          isOpen ? 'translate-x-0' : '-translate-x-full',
          'md:relative md:translate-x-0',
          isCollapsed ? 'w-16' : 'w-80'
        )}
      >
        <div className={cn('p-4 border-b flex items-center', isCollapsed ? 'justify-center' : 'justify-between')}>
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
            title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
          >
            {isCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
          </Button>
        </div>

        <div className="p-3">
          <Button
            className={cn('w-full justify-start', isCollapsed && 'justify-center px-0')}
            onClick={() => openCreateConfigDialog('new_config')}
            variant={isCollapsed ? 'outline' : 'default'}
          >
            <Plus className={cn('h-4 w-4', !isCollapsed && 'mr-2')} />
            {!isCollapsed && 'New Session'}
          </Button>
        </div>

        <Separator />

        <ScrollArea className="flex-1">
          <div className="p-3 space-y-6">
            <div className="space-y-2">
              {!isCollapsed && <h3 className="text-xs font-semibold text-muted-foreground px-2">Council Members</h3>}
              <Button
                variant="outline"
                className={cn(
                  'w-full justify-start relative',
                  isCollapsed ? 'justify-center px-0 h-10' : 'h-auto py-2'
                )}
                onClick={openReadOnlyDialog}
                disabled={!currentConversation}
              >
                <Users className={cn('h-4 w-4', !isCollapsed && 'mr-2')} />
                {!isCollapsed && (
                  <div className="flex min-w-0 flex-1 flex-col items-start text-left text-xs">
                    <span className="w-full truncate">Manage Council</span>
                    <span className="w-full truncate font-normal text-muted-foreground text-[10px]">
                      {activeFrameworkLabel}
                    </span>
                    <span className="w-full truncate font-normal text-muted-foreground text-[10px]">
                      {activeConversationModels.length} Members • {activeChairmanName}
                    </span>
                  </div>
                )}
              </Button>
            </div>

            <div className="space-y-1">
              {!isCollapsed && (
                <h3 className="text-xs font-semibold text-muted-foreground px-2 flex items-center mb-2">
                  Recent Sessions
                </h3>
              )}

              {recentConversations.map((conversation) => (
                <TooltipProvider key={conversation.id} delayDuration={0}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div
                        className={cn(
                          'group flex items-center rounded-md px-2 py-2 text-sm hover:bg-accent/50 cursor-pointer relative',
                          currentConversationId === conversation.id ? 'bg-accent text-accent-foreground font-medium' : '',
                          isCollapsed ? 'justify-center' : 'justify-between'
                        )}
                        onClick={() => onSelectConversation(conversation.id)}
                      >
                        {isCollapsed ? (
                          <History className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <div className="flex items-center gap-2 truncate pr-6 w-full">
                            <History className="h-4 w-4 text-muted-foreground shrink-0" />
                            <span className="truncate">{conversation.title}</span>
                          </div>
                        )}

                        {!isCollapsed && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 absolute right-1 opacity-50 group-hover:opacity-100 transition-opacity hover:bg-destructive/10 hover:text-destructive"
                            onClick={(event) => handleDelete(event, conversation.id)}
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                    </TooltipTrigger>
                    {isCollapsed && <TooltipContent side="right">{conversation.title}</TooltipContent>}
                  </Tooltip>
                </TooltipProvider>
              ))}
            </div>
          </div>
        </ScrollArea>

        <div className="p-3 border-t">
          <Button
            variant="ghost"
            size="sm"
            className={cn('w-full justify-start', isCollapsed && 'justify-center px-0')}
            onClick={() => openCreateConfigDialog('settings')}
          >
            <Settings className={cn('h-4 w-4', !isCollapsed && 'mr-2')} />
            {!isCollapsed && 'Settings'}
          </Button>
        </div>
      </div>

      <CouncilConfigDialog
        open={showConfigDialog}
        onOpenChange={handleDialogOpenChange}
        mode={configDialogMode}
        readOnlyConfig={{
          framework: currentConversation?.framework,
          councilModels: Array.isArray(currentConversation?.council_models) ? currentConversation.council_models : [],
          chairmanModel: currentConversation?.chairman_model || '',
        }}
        onStartSession={handleStartSession}
        isStartingSession={isCreatingSession}
        models={models}
        selectedFramework={selectedFramework}
        setSelectedFramework={setSelectedFramework}
        councilModels={councilModels}
        setCouncilModels={setCouncilModels}
        chairmanModel={chairmanModel}
        setChairmanModel={setChairmanModel}
        presets={presets}
        onSavePreset={saveNewPreset}
        activeView={configDialogView}
        setActiveView={setConfigDialogView}
        favoriteModels={favoriteModels}
        setFavoriteModels={setFavoriteModels}
        maxCouncilModels={maxCouncilModels}
        setMaxCouncilModels={handleMaxCouncilModelsChange}
      />
    </>
  );
});

export default CouncilSidebar;
