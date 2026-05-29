import Dexie, { type EntityTable } from 'dexie';

export interface DBProject {
  id: string;
  name: string;
  description: string;
  board: string;
  createdAt: string;
  updatedAt?: string;
  blocks: any[]; // JSON serialized nodes/edges
}

const db = new Dexie('ParakramDatabase') as Dexie & {
  projects: EntityTable<DBProject, 'id'>;
};

// Schema declaration:
// We only index properties we plan to query on (like id and createdAt)
db.version(1).stores({
  projects: 'id, name, createdAt'
});

export { db };
