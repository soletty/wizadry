'use client'

import { useEffect, useState } from 'react'
import { Clock, GitBranch, Folder, FileText, Code2, Eye, Trash2, Loader2, Copy, CheckCircle, ClipboardCheck, Target, Timer, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle 
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { apiClient, SessionInfo, TranscriptResponse, ConversationResponse, ConversationEntry, TestPlanResponse } from '@/lib/api'
import { formatDate, formatDuration, getStatusColor } from '@/lib/utils'

interface SessionDetailDialogProps {
  sessionId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function SessionDetailDialog({ sessionId, open, onOpenChange }: SessionDetailDialogProps) {
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [transcripts, setTranscripts] = useState<TranscriptResponse | null>(null)
  const [conversation, setConversation] = useState<ConversationResponse | null>(null)
  const [diff, setDiff] = useState<string>('')
  const [testPlan, setTestPlan] = useState<TestPlanResponse | null>(null)
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

      // Load session info, conversation, diff, and test plan in parallel
      const [sessionData, conversationData, diffData, testPlanData] = await Promise.allSettled([
        apiClient.getSession(sessionId),
        apiClient.getConversation(sessionId),
        apiClient.getSessionDiff(sessionId),
        apiClient.getTestPlan(sessionId),
      ])

      if (sessionData.status === 'fulfilled') {
        setSession(sessionData.value)
      }

      if (conversationData.status === 'fulfilled') {
        setConversation(conversationData.value)
      }

      if (diffData.status === 'fulfilled') {
        setDiff(diffData.value.diff)
      }

      if (testPlanData.status === 'fulfilled') {
        setTestPlan(testPlanData.value)
      } else {
        // Test plan might not exist for older sessions or sessions not ready for testing
        setTestPlan(null)
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
      case 'ready_to_test': return 'success'
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
        <Tabs defaultValue="overview" className="flex-1 flex flex-col min-h-0">
          <TabsList className={`grid w-full flex-shrink-0 ${testPlan ? 'grid-cols-4' : 'grid-cols-3'}`}>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="conversation">Conversation</TabsTrigger>
            <TabsTrigger value="changes">Diff</TabsTrigger>
            {testPlan && (
              <TabsTrigger value="test-plan" className="text-green-700 font-medium">
                ✅ Test Plan
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="overview" className="flex-1 mt-4 overflow-auto">
            <OverviewTab session={session} />
          </TabsContent>

          <TabsContent value="conversation" className="flex-1 mt-4 min-h-0">
            <ConversationTab 
              conversation={conversation?.conversation || []}
              loading={loading}
            />
          </TabsContent>

          <TabsContent value="changes" className="flex-1 mt-4 min-h-0">
            <DiffTab diff={diff} loading={loading} />
          </TabsContent>

          {testPlan && (
            <TabsContent value="test-plan" className="flex-1 mt-4 min-h-0">
              <TestPlanTab testPlan={testPlan} loading={loading} />
            </TabsContent>
          )}
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}

function OverviewTab({ session }: { session: SessionInfo }) {
  const [copiedItems, setCopiedItems] = useState<{ [key: string]: boolean }>({})
  
  const worktreeBranch = `wizardry-${session.session_id}`
  const repoName = session.repo_path.split('/').pop() || 'unknown'

  const copyToClipboard = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedItems(prev => ({ ...prev, [key]: true }))
      setTimeout(() => {
        setCopiedItems(prev => ({ ...prev, [key]: false }))
      }, 2000)
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
    }
  }

  const CopyButton = ({ text, copyKey, className = "" }: { text: string, copyKey: string, className?: string }) => (
    <Button
      variant="ghost"
      size="sm"
      className={`h-6 w-6 p-0 ${className}`}
      onClick={() => copyToClipboard(text, copyKey)}
    >
      {copiedItems[copyKey] ? (
        <CheckCircle className="h-3 w-3 text-green-600" />
      ) : (
        <Copy className="h-3 w-3" />
      )}
    </Button>
  )

  return (
    <div className="space-y-6 p-6">
      {/* Worktree Branch - Prominent Section */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-blue-900 mb-1">Worktree Branch</h3>
            <p className="text-sm text-blue-700 mb-3">Use this branch to checkout or merge the changes</p>
            <div className="flex items-center space-x-3">
              <code className="bg-white px-3 py-1 rounded border text-sm font-mono text-blue-800">
                {worktreeBranch}
              </code>
              <CopyButton text={worktreeBranch} copyKey="branch" />
            </div>
          </div>
          <GitBranch className="h-8 w-8 text-blue-600" />
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-gray-50 border rounded-lg p-4">
        <h3 className="font-semibold mb-3">Quick Commands</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-medium">Checkout branch:</span>
              <code className="ml-2 text-xs bg-white px-2 py-1 rounded border font-mono">
                git checkout {worktreeBranch}
              </code>
            </div>
            <CopyButton text={`git checkout ${worktreeBranch}`} copyKey="checkout" />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm font-medium">Merge to {session.base_branch}:</span>
              <code className="ml-2 text-xs bg-white px-2 py-1 rounded border font-mono">
                git checkout {session.base_branch} && git merge {worktreeBranch}
              </code>
            </div>
            <CopyButton text={`git checkout ${session.base_branch} && git merge ${worktreeBranch}`} copyKey="merge" />
          </div>
        </div>
      </div>

      {/* Session Info Grid */}
      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-4">
          <h3 className="font-semibold flex items-center">
            <Folder className="h-4 w-4 mr-2" />
            Repository Info
          </h3>
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Repository:</span>
              <div className="flex items-center space-x-2">
                <span className="font-medium">{repoName}</span>
                <CopyButton text={repoName} copyKey="repo" className="opacity-60" />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Base Branch:</span>
              <div className="flex items-center space-x-2">
                <span className="font-medium">{session.base_branch}</span>
                <CopyButton text={session.base_branch} copyKey="baseBranch" className="opacity-60" />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Session ID:</span>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-xs">{session.session_id.substring(0, 8)}...</span>
                <CopyButton text={session.session_id} copyKey="sessionId" className="opacity-60" />
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="font-semibold flex items-center">
            <Clock className="h-4 w-4 mr-2" />
            Timeline
          </h3>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Created:</span>
              <span className="font-medium">{formatDate(session.created_at)}</span>
            </div>
            {session.terminated_at && (
              <div className="flex justify-between">
                <span className="text-gray-600">Completed:</span>
                <span className="font-medium">{formatDate(session.terminated_at)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-600">Duration:</span>
              <span className="font-medium">{formatDuration(session.created_at, session.terminated_at)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


function ConversationTab({ conversation, loading }: { 
  conversation: ConversationEntry[]
  loading: boolean 
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: false
      })
    } catch {
      return timestamp
    }
  }

  if (conversation.length === 0) {
    return (
      <div className="flex-1 mx-4 mb-4 flex items-center justify-center text-gray-500">
        <div className="text-center">
          <FileText className="h-12 w-12 mx-auto mb-4 text-gray-400" />
          <p>No conversation available yet</p>
          <p className="text-sm">Agents haven't started their workflow</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      
      <div className="flex-1 mx-4 mb-4 bg-white rounded-2xl border border-gray-100 shadow-sm flex flex-col min-h-0">
        <div className="flex-1 overflow-auto p-8 space-y-6">
          {conversation.map((entry, index) => (
            <div key={index} className={`flex ${entry.agent === 'implementer' ? 'justify-start' : 'justify-end'}`}>
              <div className={`max-w-4xl rounded-2xl p-6 shadow-md hover:shadow-lg transition-all duration-200 ${
                entry.agent === 'implementer' 
                  ? 'bg-gradient-to-br from-blue-50 to-blue-100/30 border border-blue-100' 
                  : 'bg-gradient-to-br from-emerald-50 to-emerald-100/30 border border-emerald-100'
              }`}>
                {/* Agent Header */}
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center space-x-2">
                    <div className={`w-3 h-3 rounded-full shadow-sm ring-2 ring-white ${
                      entry.agent === 'implementer' ? 'bg-gradient-to-r from-blue-400 to-blue-600' : 'bg-gradient-to-r from-emerald-400 to-emerald-600'
                    }`}></div>
                    <span className={`font-semibold text-sm capitalize tracking-wide ${
                      entry.agent === 'implementer' ? 'text-blue-900' : 'text-emerald-900'
                    }`}>
                      {entry.agent}
                    </span>
                  </div>
                  <span className={`text-xs font-medium px-3 py-1 rounded-full shadow-sm ${
                    entry.agent === 'implementer' 
                      ? 'text-blue-600 bg-white/60' 
                      : 'text-emerald-600 bg-white/60'
                  }`}>
                    {formatTimestamp(entry.timestamp)}
                  </span>
                </div>

                {/* Task Section */}
                {entry.task && (
                  <div className="mb-5">
                    <div className={`text-sm font-semibold mb-3 ${
                      entry.agent === 'implementer' ? 'text-blue-800' : 'text-emerald-800'
                    }`}>Task</div>
                    <div className="bg-white/70 backdrop-blur-sm rounded-xl p-4 text-sm text-gray-800 whitespace-pre-wrap break-words border border-white/50 leading-relaxed shadow-sm">
                      {entry.task}
                    </div>
                  </div>
                )}

                {/* Response Section */}
                {entry.response && (
                  <div>
                    <div className={`text-sm font-semibold mb-3 ${
                      entry.agent === 'implementer' ? 'text-blue-800' : 'text-emerald-800'
                    }`}>Response</div>
                    <div className="bg-white/70 backdrop-blur-sm rounded-xl p-4 text-sm text-gray-800 whitespace-pre-wrap break-words border border-white/50 leading-relaxed shadow-sm">
                      {entry.response}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
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

  if (!diff) {
    return (
      <div className="flex-1 mx-4 mb-4 flex items-center justify-center text-gray-500">
        <div className="text-center">
          <Code2 className="h-12 w-12 mx-auto mb-4 text-gray-400" />
          <p>No changes detected</p>
          <p className="text-sm">Implementation may still be in progress</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex-1 mx-4 mb-4 bg-white rounded-lg border border-gray-200 flex flex-col min-h-0">
        <div className="flex-1 overflow-auto">
          <EnhancedDiffViewer diff={diff} />
        </div>
      </div>
    </div>
  )
}

function EnhancedDiffViewer({ diff }: { diff: string }) {
  const lines = diff.split('\n')
  const sections: { type: 'file' | 'hunk' | 'line'; content: string; lineType?: 'added' | 'removed' | 'context' }[] = []
  
  for (const line of lines) {
    if (line.startsWith('diff --git')) {
      // Skip git diff headers
      continue
    } else if (line.startsWith('index ')) {
      // Skip index lines
      continue
    } else if (line.startsWith('--- ') || line.startsWith('+++ ')) {
      // Parse file paths and create file headers
      if (line.startsWith('+++ ')) {
        const filePath = line.replace('+++ b/', '').replace('+++ ', '')
        if (filePath !== '/dev/null') {
          sections.push({ type: 'file', content: filePath })
        }
      }
    } else if (line.startsWith('@@')) {
      // Skip hunk headers for now - we could parse these for more context later
      continue
    } else if (line.startsWith('+')) {
      sections.push({ type: 'line', content: line.substring(1), lineType: 'added' })
    } else if (line.startsWith('-')) {
      sections.push({ type: 'line', content: line.substring(1), lineType: 'removed' })
    } else if (line.trim() !== '') {
      sections.push({ type: 'line', content: line, lineType: 'context' })
    }
  }

  return (
    <div className="font-mono text-sm">
      {sections.map((section, index) => {
        if (section.type === 'file') {
          return (
            <div key={index} className="sticky top-0 bg-gray-50 border-b border-gray-200 px-4 py-3 font-medium text-gray-700">
              <FileText className="inline h-4 w-4 mr-2" />
              {section.content}
            </div>
          )
        } else if (section.type === 'line') {
          const bgColor = section.lineType === 'added' 
            ? 'bg-green-50 border-l-2 border-green-400' 
            : section.lineType === 'removed' 
            ? 'bg-red-50 border-l-2 border-red-400'
            : 'bg-white'
          
          const textColor = section.lineType === 'added' 
            ? 'text-green-800' 
            : section.lineType === 'removed' 
            ? 'text-red-800'
            : 'text-gray-700'
          
          return (
            <div key={index} className={`px-4 py-1 ${bgColor}`}>
              <pre className={`whitespace-pre-wrap break-words leading-relaxed ${textColor}`}>
                {section.content || ' '}
              </pre>
            </div>
          )
        }
        return null
      })}
    </div>
  )
}

function TestPlanTab({ testPlan, loading }: { 
  testPlan: TestPlanResponse
  loading: boolean 
}) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    )
  }

  if (!testPlan) {
    return (
      <div className="flex-1 mx-4 mb-4 flex items-center justify-center text-gray-500">
        <div className="text-center">
          <ClipboardCheck className="h-12 w-12 mx-auto mb-4 text-gray-400" />
          <p>No test plan available</p>
          <p className="text-sm">Test plan generation may have failed or not started</p>
        </div>
      </div>
    )
  }

  // Function to render markdown content with basic formatting
  const renderMarkdown = (content: string) => {
    // Split by lines and process each line
    const lines = content.split('\n')
    const elements: JSX.Element[] = []
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]
      
      // Headers
      if (line.startsWith('### ')) {
        elements.push(<h3 key={i} className="text-lg font-semibold mt-6 mb-3 text-gray-800">{line.slice(4)}</h3>)
      } else if (line.startsWith('## ')) {
        elements.push(<h2 key={i} className="text-xl font-bold mt-8 mb-4 text-gray-900">{line.slice(3)}</h2>)
      } else if (line.startsWith('# ')) {
        elements.push(<h1 key={i} className="text-2xl font-bold mt-8 mb-4 text-gray-900">{line.slice(2)}</h1>)
      }
      // Bold text like **Objective**:
      else if (line.includes('**') && line.includes(':')) {
        const boldMatch = line.match(/\*\*(.*?)\*\*:(.*)/);
        if (boldMatch) {
          elements.push(
            <p key={i} className="mb-2">
              <strong className="font-semibold text-gray-800">{boldMatch[1]}:</strong>
              <span className="ml-1">{boldMatch[2]}</span>
            </p>
          )
        } else {
          elements.push(<p key={i} className="mb-2">{line}</p>)
        }
      }
      // List items
      else if (line.match(/^\d+\./)) {
        elements.push(<li key={i} className="ml-4 mb-1 list-decimal list-inside">{line.replace(/^\d+\./, '').trim()}</li>)
      } else if (line.startsWith('- ')) {
        elements.push(<li key={i} className="ml-4 mb-1 list-disc list-inside">{line.slice(2)}</li>)
      }
      // Code blocks (simple detection)
      else if (line.startsWith('```')) {
        // Skip code block markers
        continue
      }
      // Empty lines
      else if (line.trim() === '') {
        elements.push(<div key={i} className="mb-2"></div>)
      }
      // Regular paragraphs
      else if (line.trim().length > 0) {
        elements.push(<p key={i} className="mb-2 leading-relaxed text-gray-700">{line}</p>)
      }
    }
    
    return elements
  }

  const getComplexityColor = (complexity: string) => {
    switch (complexity.toLowerCase()) {
      case 'simple': return 'bg-green-100 text-green-800 border-green-200'
      case 'moderate': return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'complex': return 'bg-red-100 text-red-800 border-red-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Test Plan Header */}
      <div className="mx-4 mb-4 bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-lg p-4">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h2 className="text-xl font-bold text-green-900 mb-2 flex items-center">
              <ClipboardCheck className="h-6 w-6 mr-2" />
              {testPlan.feature_name}
            </h2>
            <p className="text-green-800 text-sm mb-3">{testPlan.implementation_summary}</p>
          </div>
        </div>

        {/* Test Plan Metadata */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center space-x-2">
            <Target className="h-4 w-4 text-green-600" />
            <span className="text-sm font-medium text-green-700">Complexity:</span>
            <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getComplexityColor(testPlan.test_complexity)}`}>
              {testPlan.test_complexity}
            </span>
          </div>
          
          <div className="flex items-center space-x-2">
            <Timer className="h-4 w-4 text-green-600" />
            <span className="text-sm font-medium text-green-700">Est. Time:</span>
            <span className="text-sm text-green-800">{testPlan.estimated_test_time}</span>
          </div>
          
          <div className="flex items-center space-x-2">
            <Settings className="h-4 w-4 text-green-600" />
            <span className="text-sm font-medium text-green-700">Setup Required:</span>
            <span className={`text-sm ${testPlan.requires_data_setup ? 'text-orange-700' : 'text-green-700'}`}>
              {testPlan.requires_data_setup ? 'Yes' : 'No'}
            </span>
          </div>
        </div>
      </div>

      {/* Test Plan Content */}
      <div className="flex-1 mx-4 mb-4 bg-white rounded-lg border border-gray-200 flex flex-col min-h-0">
        <div className="flex-1 overflow-auto p-6">
          <div className="prose prose-sm max-w-none">
            {renderMarkdown(testPlan.test_plan_content)}
          </div>
        </div>
      </div>
    </div>
  )
}