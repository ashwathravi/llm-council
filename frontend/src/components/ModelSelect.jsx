import { useState, useEffect, useRef } from 'react';
import './ModelSelect.css';

const ModelSelect = ({
    options,
    value,
    onChange,
    label,
    multi = false,
    maxSelected = 5,
    disabled = false
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [search, setSearch] = useState('');
    const [hoveredModel, setHoveredModel] = useState(null);
    const wrapperRef = useRef(null);
    const tooltipRef = useRef(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event) {
            if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
                setIsOpen(false);
            }
        }
        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [wrapperRef]);

    // Adjust tooltip position
    useEffect(() => {
        if (hoveredModel && tooltipRef.current && wrapperRef.current) {
            // Simple positioning logic
        }
    }, [hoveredModel]);

    // Clear hover when closed
    useEffect(() => {
        if (!isOpen) {
            setHoveredModel(null);
        }
    }, [isOpen]);

    useEffect(() => {
        if (disabled) {
            setIsOpen(false);
        }
    }, [disabled]);

    const filteredOptions = options.filter(option =>
        option.name.toLowerCase().includes(search.toLowerCase()) ||
        option.id.toLowerCase().includes(search.toLowerCase())
    );

    const handleSelect = (option) => {
        if (multi) {
            if (value.includes(option.id)) {
                onChange(value.filter(id => id !== option.id));
            } else {
                if (value.length < maxSelected) {
                    onChange([...value, option.id]);
                }
            }
        } else {
            onChange(option.id);
            setIsOpen(false);
        }
    };

    const isSelected = (option) => {
        if (multi) return value.includes(option.id);
        return value === option.id;
    };

    const getDisplayValue = () => {
        if (multi) {
            if (value.length === 0) return "Select models...";
            return `${value.length} selected`;
        }
        const selected = options.find(o => o.id === value);
        return selected ? selected.name : "Select a model...";
    };

    const getSelectedLabels = () => {
        if (!multi) return [];
        return value.map(id => {
            const opt = options.find(o => o.id === id);
            return opt ? opt.name : id;
        });
    };

    return (
        <div className="model-select-container" ref={wrapperRef}>
            <label>{label}</label>
            <div
                className={`model-select-trigger ${disabled ? 'disabled' : ''}`}
                onClick={() => {
                    if (!disabled) setIsOpen(!isOpen);
                }}
            >
                {getDisplayValue()}
                <span className="arrow">▼</span>
            </div>

            {multi && value.length > 0 && (
                <div className="selected-tags">
                    {getSelectedLabels().map(label => (
                        <span key={label} className="tag">{label}</span>
                    ))}
                </div>
            )}

            {isOpen && (
                <div className="model-select-dropdown">
                    <input
                        type="text"
                        className="model-search"
                        placeholder="Search models..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                        disabled={disabled}
                    />
                    <div className="model-options">
                        {filteredOptions.length > 0 ? (
                            filteredOptions.map(option => (
                                <div
                                    key={option.id}
                                    className={`model-option ${isSelected(option) ? 'selected' : ''}`}
                                    onClick={() => handleSelect(option)}
                                    onMouseEnter={() => setHoveredModel(option)}
                                    // Remove onMouseLeave so hover persists while moving to tooltip if needed,
                                    // but for this simple version we want it to clear specific to options.
                                    // Actually the issue is it persists when closed.
                                    // Let's keep onMouseLeave but ALSO clear on close.
                                    onMouseLeave={() => setHoveredModel(null)}
                                >
                                    {option.name}
                                    {isSelected(option) && <span className="check">✓</span>}
                                </div>
                            ))
                        ) : (
                            <div className="no-options">No models found</div>
                        )}
                    </div>
                </div>
            )}

            {/* Tooltip / Hover Card */}
            {hoveredModel && (
                <div className="model-tooltip" ref={tooltipRef}>
                    <h3>{hoveredModel.name}</h3>
                    <p className="model-description">{hoveredModel.description || "No description available."}</p>
                    <div className="model-meta">
                        <div><strong>Context:</strong> {hoveredModel.context_length ? Math.round(hoveredModel.context_length / 1000) + 'k' : 'Unknown'}</div>
                        <div><strong>Architecture:</strong> {hoveredModel.architecture?.modality || 'Unknown'}</div>
                        <div className="price-info">
                            <strong>Pricing:</strong><br />
                            Input: ${hoveredModel.pricing?.prompt || '0'} / 1M<br />
                            Output: ${hoveredModel.pricing?.completion || '0'} / 1M
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ModelSelect;
