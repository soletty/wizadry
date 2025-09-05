'use client'

import { useEffect, useState } from 'react'
import { Plus, RefreshCw, Clock, CheckCircle, XCircle, Archive, Activity } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { apiClient, SessionInfo, WebSocketClient } from '@/lib/api'
import { formatDate, getStatusColor } from '@/lib/utils'
import NewSessionDialog from '@/components/new-session-dialog'
import SessionDetailDialog from '@/components/session-detail-dialog'

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
        loadSessions() // Refresh sessions when updates arrive
      }
    })
    ws.connect()
    setWsClient(ws)

    return () => {
      ws.disconnect()
    }
  }, [])

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await apiClient.deleteSession(sessionId)
      await loadSessions()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to archive session')
    }
  }

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'completed': return 'success'
      case 'failed': return 'destructive'
      case 'in_progress': return 'pending'
      case 'terminated': return 'secondary'
      default: return 'outline'
    }
  }

  const stats = {
    total: sessions.length,
    active: sessions.filter(s => s.status === 'in_progress').length,
    completed: sessions.filter(s => s.status === 'completed').length,
    failed: sessions.filter(s => s.status === 'failed').length,
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="flex items-center space-x-2">
          <RefreshCw className="h-6 w-6 animate-spin" />
          <span>Loading sessions...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="border-b bg-white">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-semibold text-gray-900">Workflows</h1>
            </div>
            <div className="flex items-center space-x-3">
              <Button
                variant="outline"
                size="sm"
                onClick={loadSessions}
                disabled={loading}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button onClick={() => setNewSessionOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                New Workflow
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 rounded-md bg-red-50 border border-red-200 p-4">
            <div className="flex items-center">
              <XCircle className="h-5 w-5 text-red-400 mr-2" />
              <span className="text-red-700">{error}</span>
            </div>
          </div>
        )}

        {/* Stats Overview */}
        {sessions.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center space-x-6 text-sm text-gray-600">
              <span>{stats.total} total</span>
              {stats.active > 0 && (
                <span className="flex items-center space-x-1">
                  <Activity className="h-3 w-3 text-blue-500" />
                  <span>{stats.active} active</span>
                </span>
              )}
              {stats.completed > 0 && <span className="text-green-600">{stats.completed} completed</span>}
              {stats.failed > 0 && <span className="text-red-600">{stats.failed} failed</span>}
            </div>
          </div>
        )}

        {/* Sessions List */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Recent Sessions</h2>
            <span className="text-sm text-gray-500">{sessions.length} sessions</span>
          </div>

          {sessions.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-16">
                <div className="text-center">
                  <h3 className="text-lg font-medium text-gray-900 mb-2">No workflows yet</h3>
                  <p className="text-gray-500 mb-6">
                    Create your first workflow to get started.
                  </p>
                  <Button onClick={() => setNewSessionOpen(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    New Workflow
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {sessions.map((session) => (
                <Card key={session.session_id} className="hover:shadow-md transition-shadow cursor-pointer">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <CardTitle className="text-base font-medium">
                            {session.task.length > 80 
                              ? `${session.task.substring(0, 80)}...` 
                              : session.task}
                          </CardTitle>
                          <Badge variant={getStatusBadgeVariant(session.status)}>
                            {session.status}
                          </Badge>
                        </div>
                        <CardDescription className="flex items-center space-x-4 text-sm">
                          <span>{session.repo_path.split('/').pop()}</span>
                          <span className="text-gray-400">•</span>
                          <span>{session.base_branch}</span>
                          <span className="text-gray-400">•</span>
                          <span>{formatDate(session.created_at)}</span>
                        </CardDescription>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedSession(session.session_id)}
                        >
                          View Details
                        </Button>
                        {session.status !== 'archived' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDeleteSession(session.session_id)}
                            className="text-blue-600 hover:text-blue-800"
                          >
                            <Archive className="h-4 w-4 mr-1" />
                            Archive
                          </Button>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Dialogs */}
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