import { useState, useEffect } from 'react'
import { api } from '../../api/client'
import type { Entity, EntityType, EntityStatus } from '../../types'

interface EntityListProps {
  projectId: string
}

const ENTITY_TYPE_INFO: Record<EntityType, { label: string; icon: string; color: string }> = {
  REQ: { label: 'Requirement', icon: '📋', color: '#3b82f6' },
  INSTR: { label: 'Instruction', icon: '📝', color: '#f59e0b' },
  DEC: { label: 'Decision', icon: '⚖️', color: '#8b5cf6' },
  Q: { label: 'Question', icon: '❓', color: '#ef4444' },
  ASSUME: { label: 'Assumption', icon: '💭', color: '#6b7280' },
  CONST: { label: 'Constraint', icon: '🔒', color: '#dc2626' },
  RISK: { label: 'Risk', icon: '⚠️', color: '#f97316' },
  TODO: { label: 'Todo', icon: '☐', color: '#22c55e' },
  NOTE: { label: 'Note', icon: '📌', color: '#06b6d4' },
}

const STATUS_INFO: Record<EntityStatus, { label: string; color: string }> = {
  draft: { label: 'Draft', color: '#6b7280' },
  confirmed: { label: 'Confirmed', color: '#22c55e' },
  rejected: { label: 'Rejected', color: '#ef4444' },
  completed: { label: 'Completed', color: '#3b82f6' },
  superseded: { label: 'Superseded', color: '#9ca3af' },
}

export default function EntityList({ projectId }: EntityListProps) {
  const [entities, setEntities] = useState<Entity[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<EntityType | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<EntityStatus | 'all'>('all')

  useEffect(() => {
    loadEntities()
  }, [projectId])

  const loadEntities = async () => {
    try {
      const data = await api.get<Entity[]>(`/api/projects/${projectId}/entities`)
      setEntities(data)
    } catch (err) {
      console.error('Failed to load entities', err)
    } finally {
      setLoading(false)
    }
  }

  const updateEntityStatus = async (entityId: string, status: EntityStatus) => {
    try {
      await api.patch(`/api/projects/${projectId}/entities/${entityId}`, { status })
      loadEntities()
    } catch (err) {
      console.error('Failed to update entity', err)
    }
  }

  const filteredEntities = entities.filter(e => {
    if (filter !== 'all' && e.entity_type !== filter) return false
    if (statusFilter !== 'all' && e.status !== statusFilter) return false
    return true
  })

  // Group by type
  const grouped = filteredEntities.reduce((acc, entity) => {
    const type = entity.entity_type
    if (!acc[type]) acc[type] = []
    acc[type].push(entity)
    return acc
  }, {} as Record<EntityType, Entity[]>)

  if (loading) {
    return <p style={{ color: 'var(--text-secondary)' }}>Loading entities...</p>
  }

  return (
    <div className="h-full flex flex-col">
      {/* Filters */}
      <div className="flex gap-4 mb-4 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="text-sm" style={{ color: 'var(--text-secondary)' }}>Type:</label>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as EntityType | 'all')}
            className="px-2 py-1 rounded text-sm"
            style={{
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border)',
            }}
          >
            <option value="all">All Types</option>
            {Object.entries(ENTITY_TYPE_INFO).map(([type, info]) => (
              <option key={type} value={type}>
                {info.icon} {info.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm" style={{ color: 'var(--text-secondary)' }}>Status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as EntityStatus | 'all')}
            className="px-2 py-1 rounded text-sm"
            style={{
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border)',
            }}
          >
            <option value="all">All Statuses</option>
            {Object.entries(STATUS_INFO).map(([status, info]) => (
              <option key={status} value={status}>
                {info.label}
              </option>
            ))}
          </select>
        </div>

        <div className="ml-auto text-sm" style={{ color: 'var(--text-secondary)' }}>
          {filteredEntities.length} items
        </div>
      </div>

      {/* Entity List */}
      <div className="flex-1 overflow-y-auto space-y-6">
        {Object.entries(grouped).map(([type, typeEntities]) => {
          const info = ENTITY_TYPE_INFO[type as EntityType]
          return (
            <div key={type}>
              <h3
                className="text-sm font-semibold mb-2 flex items-center gap-2"
                style={{ color: info.color }}
              >
                <span>{info.icon}</span>
                <span>{info.label}s</span>
                <span
                  className="text-xs px-1.5 py-0.5 rounded-full"
                  style={{ backgroundColor: 'var(--bg-surface)' }}
                >
                  {typeEntities.length}
                </span>
              </h3>
              <div className="space-y-2">
                {typeEntities.map(entity => (
                  <EntityCard
                    key={entity.id}
                    entity={entity}
                    onStatusChange={(status) => updateEntityStatus(entity.id, status)}
                  />
                ))}
              </div>
            </div>
          )
        })}

        {filteredEntities.length === 0 && (
          <div
            className="text-center py-12"
            style={{ color: 'var(--text-secondary)' }}
          >
            <p className="text-lg mb-2">No entities found</p>
            <p className="text-sm">
              Entities are extracted from conversations using markers like REQ:, INSTR:, NOTE:
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

interface EntityCardProps {
  entity: Entity
  onStatusChange: (status: EntityStatus) => void
}

function EntityCard({ entity, onStatusChange }: EntityCardProps) {
  const typeInfo = ENTITY_TYPE_INFO[entity.entity_type]
  const statusInfo = STATUS_INFO[entity.status]
  const [expanded, setExpanded] = useState(false)

  const isActionable = entity.entity_type === 'INSTR' || entity.entity_type === 'TODO'

  return (
    <div
      className="p-3 rounded-lg border"
      style={{
        backgroundColor: 'var(--bg-surface)',
        borderColor: 'var(--border)',
      }}
    >
      {/* Header */}
      <div className="flex items-start gap-2">
        {/* Checkbox for actionable items */}
        {isActionable && (
          <button
            onClick={() => onStatusChange(
              entity.status === 'completed' ? 'draft' : 'completed'
            )}
            className="mt-0.5 w-5 h-5 rounded border flex items-center justify-center text-xs"
            style={{
              borderColor: entity.status === 'completed' ? '#22c55e' : 'var(--border)',
              backgroundColor: entity.status === 'completed' ? '#22c55e' : 'transparent',
              color: entity.status === 'completed' ? 'white' : 'transparent',
            }}
          >
            ✓
          </button>
        )}

        {/* Reference ID */}
        <span
          className="text-xs font-mono px-1.5 py-0.5 rounded"
          style={{
            backgroundColor: typeInfo.color + '20',
            color: typeInfo.color,
          }}
        >
          {entity.reference_id}
        </span>

        {/* Title */}
        <span
          className="flex-1 text-sm"
          style={{
            color: 'var(--text-primary)',
            textDecoration: entity.status === 'completed' ? 'line-through' : 'none',
            opacity: entity.status === 'completed' ? 0.7 : 1,
          }}
        >
          {entity.title}
        </span>

        {/* Priority */}
        {entity.priority && (
          <span
            className="text-xs px-1.5 py-0.5 rounded"
            style={{
              backgroundColor: entity.priority <= 2 ? '#ef4444' : '#f59e0b',
              color: 'white',
            }}
          >
            P{entity.priority}
          </span>
        )}

        {/* Status Badge */}
        <span
          className="text-xs px-1.5 py-0.5 rounded"
          style={{
            backgroundColor: statusInfo.color + '20',
            color: statusInfo.color,
          }}
        >
          {statusInfo.label}
        </span>

        {/* Expand Toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs"
          style={{ color: 'var(--text-secondary)' }}
        >
          {expanded ? '▼' : '▶'}
        </button>
      </div>

      {/* Tags */}
      {entity.tags.length > 0 && (
        <div className="flex gap-1 mt-2 ml-7">
          {entity.tags.map(tag => (
            <span
              key={tag}
              className="text-xs px-1.5 py-0.5 rounded"
              style={{
                backgroundColor: 'var(--bg-primary)',
                color: 'var(--text-secondary)',
              }}
            >
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Expanded Description */}
      {expanded && entity.description !== entity.title && (
        <div
          className="mt-2 ml-7 p-2 rounded text-sm"
          style={{
            backgroundColor: 'var(--bg-primary)',
            color: 'var(--text-secondary)',
          }}
        >
          {entity.description}
        </div>
      )}

      {/* Actions */}
      {expanded && !isActionable && (
        <div className="mt-2 ml-7 flex gap-2">
          {entity.status === 'draft' && (
            <>
              <button
                onClick={() => onStatusChange('confirmed')}
                className="text-xs px-2 py-1 rounded"
                style={{
                  backgroundColor: '#22c55e20',
                  color: '#22c55e',
                }}
              >
                ✓ Confirm
              </button>
              <button
                onClick={() => onStatusChange('rejected')}
                className="text-xs px-2 py-1 rounded"
                style={{
                  backgroundColor: '#ef444420',
                  color: '#ef4444',
                }}
              >
                ✗ Reject
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}
