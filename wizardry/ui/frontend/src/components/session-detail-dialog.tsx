'use client'

import { useEffect, useState } from 'react'
import { Clock, GitBranch, Folder, FileText, Code2, Eye, Trash2, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle 
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { apiClient, SessionInfo, TranscriptResponse } from '@/lib/api'
import { formatDate, formatDuration, getStatusColor } from '@/lib/utils'

interface SessionDetailDialogProps {
  sessionId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function SessionDetailDialog({ sessionId, open, onOpenChange }: SessionDetailDialogProps) {
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [transcripts, setTranscripts] = useState<TranscriptResponse | null>(null)
  const [diff, setDiff] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (open && sessionId) {
      loadSessionData()
    }
  }, [open, sessionId])

  const loadSessionData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Load session info, transcripts, and diff in parallel
      const [sessionData, transcriptData, diffData] = await Promise.allSettled([
        apiClient.getSession(sessionId),
        apiClient.getTranscripts(sessionId),
        apiClient.getSessionDiff(sessionId),
      ])

      if (sessionData.status === 'fulfilled') {
        setSession(sessionData.value)
      }

      if (transcriptData.status === 'fulfilled') {
        setTranscripts(transcriptData.value)
      }

      if (diffData.status === 'fulfilled') {
        setDiff(diffData.value.diff)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load session data')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!session) return
    
    try {
      setDeleting(true)
      await apiClient.deleteSession(session.session_id)
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete session')
    } finally {
      setDeleting(false)
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

  if (loading && !session) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-4xl h-[80vh]">
          <div className="flex items-center justify-center h-full">
            <div className="flex items-center space-x-2">
              <Loader2 className="h-6 w-6 animate-spin" />
              <span>Loading session details...</span>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  if (!session) {
    return null
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl h-[90vh] flex flex-col">
        <DialogHeader className="flex-shrink-0">
          <div className="flex items-start justify-between">
            <div>
              <DialogTitle className="text-xl mb-2">
                Workflow Session
              </DialogTitle>
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <span className="flex items-center">
                  <Folder className="h-4 w-4 mr-1" />
                  {session.repo_path.split('/').pop()}
                </span>
                <span className="flex items-center">
                  <GitBranch className="h-4 w-4 mr-1" />
                  {session.base_branch}
                </span>
                <span className="flex items-center">
                  <Clock className="h-4 w-4 mr-1" />
                  {formatDate(session.created_at)}
                </span>
                <Badge variant={getStatusBadgeVariant(session.status)}>
                  {session.status}
                </Badge>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              {(session.status === 'in_progress' || session.status === 'failed') && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDelete}
                  disabled={deleting}
                >
                  {deleting ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Trash2 className="h-4 w-4 mr-2" />
                  )}
                  Terminate
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={loadSessionData}>
                Refresh
              </Button>
            </div>
          </div>
        </DialogHeader>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Task Description */}
        <div className="bg-gray-50 p-4 rounded-lg">
          <h3 className="font-medium mb-2">Task Description</h3>
          <p className="text-gray-700">{session.task}</p>
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="overview" className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="implementation">Implementation</TabsTrigger>
            <TabsTrigger value="review">Review</TabsTrigger>
            <TabsTrigger value="changes">Git Changes</TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-hidden">
            <TabsContent value="overview" className="h-full">
              <OverviewTab session={session} />
            </TabsContent>

            <TabsContent value="implementation" className="h-full">
              <TranscriptTab 
                title="🔧 Implementer Agent"
                transcript={transcripts?.implementer || ''}
                loading={loading}
              />
            </TabsContent>

            <TabsContent value="review" className="h-full">
              <TranscriptTab 
                title="🔍 Reviewer Agent"
                transcript={transcripts?.reviewer || ''}
                loading={loading}
              />
            </TabsContent>

            <TabsContent value="changes" className="h-full">
              <DiffTab diff={diff} loading={loading} />
            </TabsContent>
          </div>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}

function OverviewTab({ session }: { session: SessionInfo }) {
  return (
    <div className="space-y-6 p-4">
      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-4">
          <h3 className="font-semibold">Session Details</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Session ID:</span>
              <span className="font-mono text-xs">{session.session_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Repository:</span>
              <span>{session.repo_path}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Base Branch:</span>
              <span>{session.base_branch}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Workspace:</span>
              <span className="font-mono text-xs">{session.workspace_path}</span>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="font-semibold">Timeline</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Created:</span>
              <span>{formatDate(session.created_at)}</span>
            </div>
            {session.terminated_at && (
              <div className="flex justify-between">
                <span className="text-gray-600">Terminated:</span>
                <span>{formatDate(session.terminated_at)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-600">Duration:</span>
              <span>{formatDuration(session.created_at, session.terminated_at)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Progress Indicators */}
      <div className="space-y-4">
        <h3 className="font-semibold">Progress</h3>
        <div className="space-y-3">
          <ProgressItem 
            icon="🚀" 
            text="Workflow Started" 
            completed={true} 
          />
          <ProgressItem 
            icon="🔧" 
            text="Implementation Phase" 
            completed={session.status !== 'in_progress'} 
            inProgress={session.status === 'in_progress'}
          />
          <ProgressItem 
            icon="🔍" 
            text="Review Phase" 
            completed={session.status === 'completed'} 
          />
          <ProgressItem 
            icon="✅" 
            text="Workflow Completed" 
            completed={session.status === 'completed'} 
          />
        </div>
      </div>
    </div>
  )
}

function ProgressItem({ icon, text, completed, inProgress = false }: {
  icon: string
  text: string
  completed: boolean
  inProgress?: boolean
}) {
  return (
    <div className="flex items-center space-x-3">
      <span className="text-lg">{icon}</span>
      <span className={`flex-1 ${completed ? 'text-gray-900' : inProgress ? 'text-blue-600' : 'text-gray-400'}`}>
        {text}
      </span>
      {completed && <span className="text-green-600">✓</span>}
      {inProgress && <Loader2 className="h-4 w-4 animate-spin text-blue-600" />}
    </div>
  )
}

function TranscriptTab({ title, transcript, loading }: { 
  title: string
  transcript: string
  loading: boolean 
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col p-4">
      <h3 className="font-semibold mb-4">{title}</h3>
      {transcript ? (
        <div className="flex-1 bg-gray-50 rounded-lg border min-h-0 flex flex-col">
          <div className="flex-1 overflow-auto p-4">
            <div className="text-sm leading-relaxed whitespace-pre-wrap break-words max-w-none">
              {transcript}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <FileText className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p>No transcript available yet</p>
            <p className="text-sm">Agent hasn't started or completed this phase</p>
          </div>
        </div>
      )}
    </div>
  )
}

function DiffTab({ diff, loading }: { diff: string; loading: boolean }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col p-4">
      <h3 className="font-semibold mb-4">📝 Code Changes</h3>
      {diff ? (
        <div className="flex-1 bg-gray-900 rounded-lg border min-h-0 flex flex-col">
          <div className="flex-1 overflow-auto p-4">
            <pre className="text-sm text-gray-100 font-mono whitespace-pre-wrap break-words leading-relaxed">{diff}</pre>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          <div className="text-center">
            <Code2 className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            <p>No changes detected</p>
            <p className="text-sm">Implementation may still be in progress</p>
          </div>
        </div>
      )}
    </div>
  )
}