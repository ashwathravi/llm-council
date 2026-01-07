
import React, { useState } from 'react';
import { Check, ChevronsUpDown, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

const ModelSelector = ({
    options = [],
    value,
    onChange,
    label,
    multi = false,
    maxSelected = 5,
    disabled = false,
    placeholder = "Select model..."
}) => {
    const [open, setOpen] = useState(false);
    const [search, setSearch] = useState("");
    const [hoveredModel, setHoveredModel] = useState(null);

    const filteredOptions = options.filter((option) =>
        option.name.toLowerCase().includes(search.toLowerCase()) ||
        option.id.toLowerCase().includes(search.toLowerCase())
    );

    const handleSelect = (optionId) => {
        if (multi) {
            if (value.includes(optionId)) {
                onChange(value.filter((id) => id !== optionId));
            } else {
                if (value.length < maxSelected) {
                    onChange([...value, optionId]);
                }
            }
        } else {
            onChange(optionId);
            setOpen(false);
        }
    };

    const isSelected = (optionId) => {
        if (multi) return value.includes(optionId);
        return value === optionId;
    };

    const getDisplayLabel = () => {
        if (multi) {
            if (!value || value.length === 0) return placeholder;
            return `${value.length} selected`;
        }
        const selectedOption = options.find(op => op.id === value);
        return selectedOption ? selectedOption.name : placeholder;
    };

    const getSelectedModels = () => {
        if (!multi) return [];
        return options.filter(op => value.includes(op.id));
    }

    return (
        <div className="flex flex-col gap-2">
            {label && <span className="text-sm font-medium">{label}</span>}
            <Popover open={open} onOpenChange={setOpen}>
                <PopoverTrigger asChild>
                    <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={open}
                        className="w-full justify-between font-normal"
                        disabled={disabled}
                    >
                        {getDisplayLabel()}
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                </PopoverTrigger>
                <PopoverContent className="w-[300px] p-0" align="start">
                    <div className="flex items-center border-b px-3">
                        <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                        <Input
                            className="flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 border-none focus-visible:ring-0 focus-visible:ring-offset-0"
                            placeholder="Search models..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                    </div>

                    <div className="flex">
                        <ScrollArea className="h-64 w-full">
                            <div className="p-1">
                                {filteredOptions.length === 0 && (
                                    <div className="py-6 text-center text-sm text-muted-foreground">
                                        No models found.
                                    </div>
                                )}
                                {filteredOptions.map((option) => (
                                    <div
                                        key={option.id}
                                        className={cn(
                                            "relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
                                            isSelected(option.id) && "bg-accent text-accent-foreground"
                                        )}
                                        onClick={() => handleSelect(option.id)}
                                        onMouseEnter={() => setHoveredModel(option)}
                                    >
                                        <Check
                                            className={cn(
                                                "mr-2 h-4 w-4",
                                                isSelected(option.id) ? "opacity-100" : "opacity-0"
                                            )}
                                        />
                                        <span className="truncate">{option.name}</span>
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>

                    </div>
                </PopoverContent>
            </Popover>

            {/* Selected Tags for Multi-Select */}
            {multi && value.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                    {getSelectedModels().map(model => (
                        <Badge key={model.id} variant="secondary" className="text-xs">
                            {model.name}
                            <button
                                className="ml-1 ring-offset-background rounded-full outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    handleSelect(model.id);
                                }}
                            >
                                <X className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                            </button>
                        </Badge>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ModelSelector;
