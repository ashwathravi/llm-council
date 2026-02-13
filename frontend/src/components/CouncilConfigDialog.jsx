import { useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Check, Crown, Save, Settings2, Star, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const COUNCIL_TYPES = [
  {
    id: 'standard',
    name: 'Standard Council',
    framework: 'standard',
    description: 'Models answer individually, rank each other, and a Chairman synthesizes the best answer.',
  },
  {
    id: 'debate',
    name: 'Chain of Debate',
    framework: 'debate',
    description: "Models answer, then critique each other's arguments to find logical flaws before synthesis.",
  },
  {
    id: 'six_hats',
    name: 'Six Thinking Hats',
    framework: 'six_hats',
    description: 'Models are assigned specific cognitive perspectives (Facts, Feelings, Risks, Benefits, Creativity, Process) to ensure holistic coverage.',
  },
  {
    id: 'ensemble',
    name: 'Ensemble (Fast)',
    framework: 'ensemble',
    description: 'Parallel execution for quick consensus without the peer-review stage.',
  },
];

const clampSelectionLimit = (value) => {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 5;
  return Math.max(1, Math.min(10, Math.floor(parsed)));
};

const getFrameworkLabel = (framework) => {
  const type = COUNCIL_TYPES.find((item) => item.framework === framework);
  return type?.name || framework || 'Standard Council';
};

const CouncilConfigDialog = ({
  open,
  onOpenChange,
  mode = 'create',
  readOnlyConfig,
  onStartSession,
  isStartingSession = false,
  models,
  selectedFramework,
  setSelectedFramework,
  councilModels,
  setCouncilModels,
  chairmanModel,
  setChairmanModel,
  presets,
  onSavePreset,
  activeView,
  setActiveView,
  favoriteModels,
  setFavoriteModels,
  maxCouncilModels,
  setMaxCouncilModels,
}) => {
  const [activePresetId, setActivePresetId] = useState(null);
  const [memberView, setMemberView] = useState('all');

  const favoriteModelSet = useMemo(() => new Set(favoriteModels), [favoriteModels]);

  const favoriteModelOptions = useMemo(
    () => models.filter((model) => favoriteModelSet.has(model.id)),
    [models, favoriteModelSet]
  );

  const selectedChairman = useMemo(
    () => models.find((model) => model.id === chairmanModel) || null,
    [models, chairmanModel]
  );

  const getModelName = (modelId) => models.find((model) => model.id === modelId)?.name || modelId;

  const applySavedPreset = (preset) => {
    setActivePresetId(preset.id);

    const nextFramework = preset.framework || 'standard';
    const requestedChairman = preset.chairmanModel || '';
    const requestedCouncilModels = Array.isArray(preset.councilModels) ? preset.councilModels : [];

    const availableModelIds = new Set(models.map((model) => model.id));
    const validCouncilModels = requestedCouncilModels
      .filter((modelId) => availableModelIds.has(modelId))
      .slice(0, maxCouncilModels);

    setSelectedFramework(nextFramework);
    setCouncilModels(validCouncilModels);
    setChairmanModel(requestedChairman && availableModelIds.has(requestedChairman) ? requestedChairman : '');
    setActiveView('new_config');
  };

  const toggleModel = (modelId) => {
    setActivePresetId(null);

    if (councilModels.includes(modelId)) {
      const updatedModels = councilModels.filter((id) => id !== modelId);
      setCouncilModels(updatedModels);
      return;
    }

    if (councilModels.length >= maxCouncilModels) {
      return;
    }

    setCouncilModels([...councilModels, modelId]);
  };

  const toggleFavorite = (modelId) => {
    setFavoriteModels((currentFavorites) => {
      if (currentFavorites.includes(modelId)) {
        return currentFavorites.filter((id) => id !== modelId);
      }
      return [...currentFavorites, modelId];
    });
  };

  const handleMaxSelectionChange = (value) => {
    setMaxCouncilModels(clampSelectionLimit(value));
    setActivePresetId(null);
  };

  const renderModelRows = (modelList, allowFavoriteToggle) => {
    if (modelList.length === 0) {
      return (
        <div className="p-4 text-sm text-muted-foreground">
          {allowFavoriteToggle
            ? 'No models available.'
            : 'No favorites yet. Mark models as favorite from the All Models tab.'}
        </div>
      );
    }

    return modelList.map((model) => {
      const isActive = councilModels.includes(model.id);
      const isChairman = chairmanModel === model.id;
      const isFavorite = favoriteModelSet.has(model.id);

      return (
        <div key={model.id} className="flex items-center justify-between gap-3 p-3 border-b last:border-0 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-3 min-w-0">
            <Switch
              checked={isActive}
              onCheckedChange={() => toggleModel(model.id)}
            />
            <div className="min-w-0">
              <div className="text-sm font-medium flex items-center gap-2">
                <span className="truncate">{model.name}</span>
                {isChairman && (
                  <Badge variant="default" className="bg-amber-500 hover:bg-amber-600 text-white h-5 px-1.5 gap-0.5">
                    <Crown className="h-3 w-3" /> Chairman
                  </Badge>
                )}
              </div>
              <div className="text-xs text-muted-foreground truncate">{model.id}</div>
            </div>
          </div>

          <div className="flex items-center gap-1 shrink-0">
            {allowFavoriteToggle && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => toggleFavorite(model.id)}
                title={isFavorite ? 'Remove from favorites' : 'Mark as favorite'}
              >
                <Star className={cn('h-4 w-4', isFavorite ? 'text-amber-500 fill-amber-500' : 'text-muted-foreground')} />
              </Button>
            )}

            <Button
              type="button"
              variant={isChairman ? 'default' : 'outline'}
              size="sm"
              className="h-7 text-xs"
              onClick={() => {
                setChairmanModel(model.id);
                setActivePresetId(null);
              }}
            >
              {isChairman ? 'Chairman' : 'Set Chair'}
            </Button>
          </div>
        </div>
      );
    });
  };

  const renderReadOnlyConversationConfig = () => {
    const framework = readOnlyConfig?.framework || 'standard';
    const selectedModels = Array.isArray(readOnlyConfig?.councilModels) ? readOnlyConfig.councilModels : [];
    const readOnlyChairman = readOnlyConfig?.chairmanModel || '';

    return (
      <div className="flex-1 overflow-y-auto px-6 py-2">
        <div className="space-y-6 pb-6">
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-muted-foreground">Council Type</h3>
            <Card className="border-primary/30 bg-accent/10">
              <CardContent className="p-4">
                <div className="font-semibold text-primary">{getFrameworkLabel(framework)}</div>
                <p className="text-sm text-muted-foreground mt-1">This configuration is frozen for the active conversation.</p>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-muted-foreground">Summary</h3>
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">{selectedModels.length} Selected Models</Badge>
              <Badge variant="outline">Chairman: {readOnlyChairman ? getModelName(readOnlyChairman) : 'Auto'}</Badge>
            </div>
          </div>

          <div className="space-y-3 rounded-md border bg-card p-4">
            <h3 className="text-sm font-semibold text-muted-foreground">Selected Models</h3>
            {selectedModels.length === 0 ? (
              <p className="text-sm text-muted-foreground">No explicit models selected for this conversation.</p>
            ) : (
              <div className="space-y-2">
                {selectedModels.map((modelId) => (
                  <div key={modelId} className="text-sm">
                    <span className="font-medium">{getModelName(modelId)}</span>
                    <span className="text-xs text-muted-foreground ml-2">{modelId}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderCreateConfig = () => (
    <Tabs value={activeView} onValueChange={setActiveView} className="flex flex-1 min-h-0 flex-col">
      <div className="px-6 pb-2">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="new_config" className="gap-2">
            <Users className="h-4 w-4" />
            New Config
          </TabsTrigger>
          <TabsTrigger value="load_saved_config" className="gap-2">
            <Save className="h-4 w-4" />
            Load Saved Config
          </TabsTrigger>
          <TabsTrigger value="settings" className="gap-2">
            <Settings2 className="h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-2">
        <TabsContent value="new_config" className="mt-0 space-y-6 pb-6">
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-muted-foreground">Council Types</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {COUNCIL_TYPES.map((type) => (
                <Card
                  key={type.id}
                  className={cn(
                    'cursor-pointer hover:bg-accent/50 transition-colors relative',
                    selectedFramework === type.framework ? 'border-primary bg-accent/20' : ''
                  )}
                  onClick={() => {
                    setSelectedFramework(type.framework);
                    setActivePresetId(null);
                  }}
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="font-semibold text-primary">{type.name}</div>
                      {selectedFramework === type.framework && <Check className="h-4 w-4 text-primary" />}
                    </div>
                    <p className="text-sm text-foreground/90">{type.description}</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-muted-foreground">Council Members</h3>
              <div className="text-xs text-muted-foreground">{councilModels.length}/{maxCouncilModels} Active</div>
            </div>

            <Tabs value={memberView} onValueChange={setMemberView} className="space-y-2">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="all">All Models</TabsTrigger>
                <TabsTrigger value="favorites">Favorites</TabsTrigger>
              </TabsList>

              <TabsContent value="all" className="mt-0">
                <div className="rounded-md border bg-card">
                  {renderModelRows(models, true)}
                </div>
              </TabsContent>

              <TabsContent value="favorites" className="mt-0">
                <div className="rounded-md border bg-card">
                  {renderModelRows(favoriteModelOptions, false)}
                </div>
              </TabsContent>
            </Tabs>
          </div>

          <div className="space-y-2 rounded-md border bg-card p-4">
            <h3 className="text-sm font-semibold text-muted-foreground">Chairman</h3>
            <p className="text-sm text-muted-foreground">
              {selectedChairman ? `${selectedChairman.name} (${selectedChairman.id})` : 'No chairman selected'}
            </p>
            {selectedChairman && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-fit"
                onClick={() => setChairmanModel('')}
              >
                Clear Chairman
              </Button>
            )}
          </div>
        </TabsContent>

        <TabsContent value="load_saved_config" className="mt-0 space-y-6 pb-6">
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-muted-foreground">Saved Presets</h3>
              <div className="text-xs text-muted-foreground">{presets.length} Saved</div>
            </div>

            {presets.length === 0 ? (
              <div className="rounded-md border bg-card p-4 text-sm text-muted-foreground">
                No saved presets yet. Save your current configuration to reuse it.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {presets.map((preset) => (
                  <Card
                    key={preset.id}
                    className={cn(
                      'cursor-pointer hover:bg-accent/50 transition-colors relative',
                      activePresetId === preset.id ? 'border-primary bg-accent/20' : ''
                    )}
                    onClick={() => applySavedPreset(preset)}
                  >
                    <CardContent className="p-4">
                      <div className="flex justify-between items-start mb-2">
                        <div className="font-semibold text-sm">{preset.name}</div>
                        {activePresetId === preset.id && <Check className="h-4 w-4 text-primary" />}
                      </div>
                      <p className="text-xs text-muted-foreground">{preset.description}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="settings" className="mt-0 space-y-6 pb-6">
          <div className="space-y-3 rounded-md border bg-card p-4">
            <h3 className="text-sm font-semibold text-muted-foreground">Model Selection Preferences</h3>
            <div className="space-y-2">
              <label className="text-sm font-medium">Allowed number of model selections</label>
              <Select value={String(maxCouncilModels)} onValueChange={handleMaxSelectionChange}>
                <SelectTrigger className="w-full sm:w-[240px]">
                  <SelectValue placeholder="Select maximum" />
                </SelectTrigger>
                <SelectContent>
                  {Array.from({ length: 10 }, (_, index) => index + 1).map((value) => (
                    <SelectItem key={value} value={String(value)}>
                      {value} {value === 1 ? 'model' : 'models'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                This limit applies when selecting council members in this workspace.
              </p>
            </div>
          </div>

          <div className="space-y-2 rounded-md border bg-card p-4">
            <h3 className="text-sm font-semibold text-muted-foreground">Favorites</h3>
            <p className="text-sm text-muted-foreground">
              {favoriteModels.length} models are currently marked as favorites.
            </p>
          </div>
        </TabsContent>
      </div>
    </Tabs>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden flex flex-col p-0 gap-0">
        <DialogHeader className="p-6 pb-2">
          <DialogTitle className="text-xl">
            {mode === 'read_only' ? 'Active Conversation Council' : 'Council Configuration'}
          </DialogTitle>
          <DialogDescription>
            {mode === 'read_only'
              ? 'Conversation configuration is read-only after session creation.'
              : 'Configure council type, members, favorites, and selection preferences before starting a session.'}
          </DialogDescription>
        </DialogHeader>

        {mode === 'read_only' ? renderReadOnlyConversationConfig() : renderCreateConfig()}

        <DialogFooter className="p-4 border-t bg-muted/20 flex sm:justify-between items-center gap-2">
          {mode === 'create' && activeView === 'new_config' && (
            <Button variant="outline" className="w-full sm:w-auto" onClick={onSavePreset}>
              <Save className="mr-2 h-4 w-4" />
              Save Config
            </Button>
          )}
          <div className="flex w-full sm:w-auto gap-2 sm:ml-auto">
            <Button variant="outline" onClick={() => onOpenChange(false)} className="w-full sm:w-auto">
              {mode === 'read_only' ? 'Close' : 'Cancel'}
            </Button>
            {mode === 'create' && (
              <Button
                onClick={onStartSession}
                className="w-full sm:w-auto"
                disabled={isStartingSession}
              >
                {isStartingSession ? 'Starting...' : 'Start Session'}
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default CouncilConfigDialog;
