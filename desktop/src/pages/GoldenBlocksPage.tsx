import { useState } from 'react';

const CATEGORIES = [
  'sensor', 'actuator', 'audio', 'display', 'communication',
  'control_blocks', 'freertos', 'power', 'security', 'storage'
];

function GoldenBlocksPage() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  return (
    <div>
      <div className="page-header">
        <h2>Golden Blocks (248)</h2>
        <p>Pre-compiled, zero-code firmware templates</p>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
        <button
          className={`btn ${!selectedCategory ? 'btn-primary' : ''}`}
          onClick={() => setSelectedCategory(null)}
        >
          All
        </button>
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            className={`btn ${selectedCategory === cat ? 'btn-primary' : ''}`}
            onClick={() => setSelectedCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      <div className="card">
        <p style={{ color: 'var(--text-secondary)' }}>
          {selectedCategory
            ? `Showing ${selectedCategory} golden blocks. Connect to the backend to load block details.`
            : 'Select a category to browse golden blocks, or connect to the backend for the full catalog.'
          }
        </p>
      </div>
    </div>
  );
}

export default GoldenBlocksPage;
