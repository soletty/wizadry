// API client for Wizardry backend

export interface SessionInfo {
  session_id: string
  repo_path: string
  base_branch: string
  task: string
  status: string
  created_at: string
  workspace_path: string
  terminated_at?: string
}

export interface TranscriptResponse {
  implementer: string
  reviewer: string
}

export interface ConversationEntry {
  timestamp: string
  agent: string // "implementer" or "reviewer"
  task: string
  response: string
}

export interface ConversationResponse {
  conversation: ConversationEntry[]
}

export interface RepoInfo {
  path: string
  name: string
  branches: string[]
  current_branch: string
  is_clean: boolean
  remote_url?: string
}

export interface CreateSessionRequest {
  repo_path: string
  base_branch: string
  task: string
  no_cleanup?: boolean
  max_iterations?: number
}

export interface TestPlanResponse {
  feature_name: string
  implementation_summary: string
  test_complexity: string
  estimated_test_time: string
  requires_data_setup: boolean
  confidence: number
  test_plan_content: string
  test_plan_generated: boolean
}

class ApiClient {
  private baseUrl: string

  constructor(baseUrl?: string) {
    // Try to get API URL from environment, fallback to default
    this.baseUrl = baseUrl || 
      process.env.NEXT_PUBLIC_API_URL || 
      'http://localhost:8001/api'
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(error || `HTTP ${response.status}`)
    }

    return response.json()
  }

  async getSessions(): Promise<SessionInfo[]> {
    return this.request<SessionInfo[]>('/sessions')
  }

  async getSession(sessionId: string): Promise<SessionInfo> {
    return this.request<SessionInfo>(`/sessions/${sessionId}`)
  }

  async getTranscripts(sessionId: string): Promise<TranscriptResponse> {
    return this.request<TranscriptResponse>(`/sessions/${sessionId}/transcripts`)
  }

  async getConversation(sessionId: string): Promise<ConversationResponse> {
    return this.request<ConversationResponse>(`/sessions/${sessionId}/conversation`)
  }

  async getSessionDiff(sessionId: string): Promise<{ diff: string }> {
    return this.request<{ diff: string }>(`/sessions/${sessionId}/diff`)
  }

  async deleteSession(sessionId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/sessions/${sessionId}`, {
      method: 'DELETE'
    })
  }

  async archiveSession(sessionId: string, cleanupBranch: boolean = true): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/sessions/${sessionId}/archive?cleanup_branch=${cleanupBranch}`, {
      method: 'POST'
    })
  }

  async createSession(request: CreateSessionRequest): Promise<{ message: string; repo_path: string; branch: string; task: string }> {
    return this.request<{ message: string; repo_path: string; branch: string; task: string }>('/sessions', {
      method: 'POST',
      body: JSON.stringify(request)
    })
  }

  async discoverRepos(searchPath: string = '.'): Promise<RepoInfo[]> {
    return this.request<RepoInfo[]>(`/repos?search_path=${encodeURIComponent(searchPath)}`)
  }

  async getRepoInfo(repoPath: string): Promise<RepoInfo> {
    return this.request<RepoInfo>(`/repos/info?repo_path=${encodeURIComponent(repoPath)}`)
  }

  async getTestPlan(sessionId: string): Promise<TestPlanResponse> {
    return this.request<TestPlanResponse>(`/sessions/${sessionId}/test-plan`)
  }
}

export const apiClient = new ApiClient()

// WebSocket client for real-time updates
export class WebSocketClient {
  private ws: WebSocket | null = null
  private url: string
  private onMessage: (data: any) => void

  constructor(onMessage: (data: any) => void, wsUrl?: string) {
    // Try to get WebSocket URL from environment, fallback to default
    this.url = wsUrl || 
      process.env.NEXT_PUBLIC_WS_URL || 
      'ws://localhost:8001/api/ws'
    this.onMessage = onMessage
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url)
      
      this.ws.onopen = () => {
        console.log('WebSocket connected')
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.onMessage(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    }
  }
}