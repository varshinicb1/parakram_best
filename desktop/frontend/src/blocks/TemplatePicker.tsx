/**
 * TemplatePicker — Browse and load pre-built project templates.
 */

import { useState, useEffect } from 'react';
import { templateApi } from '../api/apiClient';

interface Template {
    id: string;
    name: string;
    description: string;
    icon: string;
    category: string;
    blocks: number;
    preview_tags: string[];
}

interface Props {
    onLoad: (templateData: unknown) => void;
}

export default function TemplatePicker({ onLoad }: Props) {
    const [templates, setTemplates] = useState<Template[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedId, setSelectedId] = useState<string | null>(null);

    useEffect(() => {
        templateApi.list()
            .then((data) => setTemplates((data.templates || []) as Template[]))
            .catch(() => setTemplates([]));
    }, []);

    const handleLoad = async (id: string) => {
        setLoading(true);
        setSelectedId(id);
        try {
            const data = await templateApi.get(id);
            onLoad(data);
        } catch (err) {
            console.error('Failed to load template:', err);
        } finally {
            setLoading(false);
            setSelectedId(null);
        }
    };

    return (
        <div className="template-picker">
            <div className="template-picker__header">
                <span>🚀 Project Templates</span>
            </div>
            <div className="template-picker__grid">
                {templates.map((t) => (
                    <button
                        key={t.id}
                        className={`template-card ${selectedId === t.id ? 'template-card--loading' : ''}`}
                        onClick={() => handleLoad(t.id)}
                        disabled={loading}
                    >
                        <span className="template-card__icon">{t.icon}</span>
                        <span className="template-card__name">{t.name}</span>
                        <span className="template-card__desc">{t.description}</span>
                        <div className="template-card__tags">
                            {(t.preview_tags || []).slice(0, 3).map((tag, i) => (
                                <span key={i} className="template-card__tag">{tag}</span>
                            ))}
                        </div>
                        <span className="template-card__blocks">{t.blocks} blocks</span>
                    </button>
                ))}
                {templates.length === 0 && (
                    <div className="template-picker__empty">Loading templates...</div>
                )}
            </div>
        </div>
    );
}
