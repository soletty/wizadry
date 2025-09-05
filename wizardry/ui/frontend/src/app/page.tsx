'use client'

import { useEffect, useState } from 'react'
import { Plus, Trash2, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { apiClient, SessionInfo, WebSocketClient } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import NewSessionDialog from '@/components/new-session-dialog'
import SessionDetailDialog from '@/components/session-detail-dialog'

interface GroupedSessions {
  [key: string]: SessionInfo[]
}

export default function Dashboard() {
  const [sessions, setSessions] = useState<SessionInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [newSessionOpen, setNewSessionOpen] = useState(false)
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const [wsClient, setWsClient] = useState<WebSocketClient | null>(null)

  const loadSessions = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getSessions()
      setSessions(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSessions()

    // Setup WebSocket for real-time updates
    const ws = new WebSocketClient((data) => {
      if (data.type === 'session_terminated' || data.type === 'workflow_completed' || data.type === 'session_archived') {
        loadSessions() // Auto-refresh when updates arrive
      }
    })
    ws.connect()
    setWsClient(ws)

    return () => {
      ws.disconnect()
    }
  }, [])

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await apiClient.deleteSession(sessionId)
      await loadSessions()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to archive session')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800'
      case 'failed': return 'bg-red-100 text-red-800'
      case 'in_progress': return 'bg-blue-100 text-blue-800'
      case 'terminated': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  // Group sessions by repo/branch combination
  const groupedSessions: GroupedSessions = sessions.reduce((acc, session) => {
    const key = `${session.repo_path.split('/').pop()}/${session.base_branch}`
    if (!acc[key]) {
      acc[key] = []
    }
    acc[key].push(session)
    return acc
  }, {} as GroupedSessions)

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-white">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (sessions.length === 0) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="max-w-2xl mx-auto p-6">
          {error && (
            <div className="border-l-4 border-red-400 bg-red-50 p-4 mb-6">
              <div className="text-sm text-red-700">{error}</div>
            </div>
          )}
          
          <div className="text-center">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Plus className="h-8 w-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No workflows yet</h3>
            <p className="text-gray-500 mb-6 max-w-sm mx-auto">
              Create your first workflow to get started with automated code implementation.
            </p>
            <Button 
              onClick={() => setNewSessionOpen(true)}
              className="bg-black hover:bg-gray-800 text-white"
            >
              <Plus className="h-4 w-4 mr-2" />
              Create Workflow
            </Button>
          </div>
        </div>

        <NewSessionDialog 
          open={newSessionOpen}
          onOpenChange={setNewSessionOpen}
          onSuccess={loadSessions}
        />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white">
      {error && (
        <div className="border-l-4 border-red-400 bg-red-50 p-4 mb-6">
          <div className="text-sm text-red-700">{error}</div>
        </div>
      )}

      <div className="max-w-4xl mx-auto p-6">
        {Object.entries(groupedSessions).map(([repoBranch, sessionGroup]) => (
          <div key={repoBranch} className="mb-8">
            <div className="flex items-center space-x-2 mb-4">
              <h2 className="text-sm font-medium text-gray-900">{repoBranch}</h2>
              <span className="text-xs text-gray-400">
                {sessionGroup.length} workflow{sessionGroup.length !== 1 ? 's' : ''}
              </span>
            </div>
            
            <div className="space-y-3">
              {sessionGroup.map((session) => (
                <div
                  key={session.session_id}
                  onClick={() => setSelectedSession(session.session_id)}
                  className="group p-4 border border-gray-200 rounded-lg hover:border-gray-300 cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-3 mb-2">
                        <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(session.status)}`}>
                          {session.status === 'in_progress' ? 'running' : session.status}
                        </div>
                        <span className="text-xs text-gray-400">
                          {formatDate(session.created_at)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-900 leading-5">
                        {session.task.length > 120 
                          ? `${session.task.substring(0, 120)}...` 
                          : session.task}
                      </p>
                    </div>
                    <div className="ml-4">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => handleDeleteSession(session.session_id, e)}
                        className="text-gray-400 hover:text-red-500"
                        title="Archive workflow"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Simple floating action button */}
      <Button 
        onClick={() => setNewSessionOpen(true)}
        className="fixed bottom-6 right-6 h-12 w-12 bg-black hover:bg-gray-800 text-white shadow-lg rounded-full p-0"
      >
        <Plus className="h-6 w-6" />
      </Button>

      {/* Use the original working modal */}
      <NewSessionDialog 
        open={newSessionOpen}
        onOpenChange={setNewSessionOpen}
        onSuccess={loadSessions}
      />
      
      {selectedSession && (
        <SessionDetailDialog
          sessionId={selectedSession}
          open={!!selectedSession}
          onOpenChange={(open) => !open && setSelectedSession(null)}
        />
      )}
    </div>
  )
}