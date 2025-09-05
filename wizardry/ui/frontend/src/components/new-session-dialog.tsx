'use client'

import { useEffect, useState } from 'react'
import { Folder, GitBranch, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle 
} from '@/components/ui/dialog'
import { apiClient, RepoInfo, CreateSessionRequest } from '@/lib/api'

interface NewSessionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export default function NewSessionDialog({ open, onOpenChange, onSuccess }: NewSessionDialogProps) {
  const [repos, setRepos] = useState<RepoInfo[]>([])
  const [selectedRepo, setSelectedRepo] = useState<string>('')
  const [selectedBranch, setSelectedBranch] = useState<string>('')
  const [task, setTask] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [discovering, setDiscovering] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load saved preferences from localStorage
  useEffect(() => {
    const savedRepo = localStorage.getItem('wizardry-last-repo')
    const savedBranch = localStorage.getItem('wizardry-last-branch')
    if (savedRepo) setSelectedRepo(savedRepo)
    if (savedBranch) setSelectedBranch(savedBranch)
  }, [])

  useEffect(() => {
    if (open) {
      discoverRepos()
      setTask('')
      setError(null)
    }
  }, [open])

  const discoverRepos = async () => {
    try {
      setDiscovering(true)
      const commonPaths = ['.', '..', process.env.HOME || '~']
      let allRepos: RepoInfo[] = []
      
      for (const path of commonPaths) {
        try {
          const repos = await apiClient.discoverRepos(path)
          allRepos = [...allRepos, ...repos]
        } catch (err) {
          // Ignore individual path errors
        }
      }
      
      // Remove duplicates based on path
      const uniqueRepos = allRepos.filter((repo, index, self) => 
        index === self.findIndex(r => r.path === repo.path)
      )
      
      setRepos(uniqueRepos)
      
      if (uniqueRepos.length > 0) {
        setSelectedRepo(uniqueRepos[0].path)
        setSelectedBranch(uniqueRepos[0].current_branch)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to discover repositories')
    } finally {
      setDiscovering(false)
    }
  }

  const handleRepoChange = (repoPath: string) => {
    setSelectedRepo(repoPath)
    const repo = repos.find(r => r.path === repoPath)
    if (repo) {
      setSelectedBranch(repo.current_branch)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!selectedRepo || !selectedBranch || !task.trim()) {
      setError('Please fill in all fields')
      return
    }

    try {
      setLoading(true)
      setError(null)

      const request: CreateSessionRequest = {
        repo_path: selectedRepo,
        base_branch: selectedBranch,
        task: task.trim(),
        no_cleanup: false,
        max_iterations: 2,
      }

      await apiClient.createSession(request)
      
      // Save preferences to localStorage
      localStorage.setItem('wizardry-last-repo', selectedRepo)
      localStorage.setItem('wizardry-last-branch', selectedBranch)
      
      onSuccess()
      onOpenChange(false)
      
      // Reset form
      setTask('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create session')
    } finally {
      setLoading(false)
    }
  }

  const selectedRepoInfo = repos.find(r => r.path === selectedRepo)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Workflow</DialogTitle>
          <DialogDescription>
            Set up a new AI workflow to automatically implement code changes in your repository.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Repository Selection */}
          <div className="space-y-3">
            <label className="text-sm font-medium">Repository</label>
            {discovering ? (
              <div className="flex items-center space-x-2 p-3 border rounded-md">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-gray-600">Discovering repositories...</span>
              </div>
            ) : repos.length > 0 ? (
              <select
                value={selectedRepo}
                onChange={(e) => handleRepoChange(e.target.value)}
                className="w-full p-3 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                {repos.map((repo) => (
                  <option key={repo.path} value={repo.path}>
                    {repo.name} ({repo.path})
                  </option>
                ))}
              </select>
            ) : (
              <div className="p-3 border rounded-md bg-gray-50">
                <div className="flex items-center space-x-2">
                  <Folder className="h-4 w-4 text-gray-400" />
                  <span className="text-sm text-gray-600">No Git repositories found</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Make sure you have Git repositories in your current directory or common paths.
                </p>
              </div>
            )}
          </div>

          {/* Repository Info */}
          {selectedRepoInfo && (
            <div className="p-3 bg-gray-50 border rounded-md">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Current: <span className="font-medium">{selectedRepoInfo.current_branch}</span></span>
                <span className="text-gray-600">{selectedRepoInfo.is_clean ? '✓ Clean' : '⚠ Uncommitted changes'}</span>
              </div>
            </div>
          )}

          {/* Branch Selection */}
          {selectedRepoInfo && (
            <div className="space-y-3">
              <label className="text-sm font-medium">Base Branch</label>
              <select
                value={selectedBranch}
                onChange={(e) => setSelectedBranch(e.target.value)}
                className="w-full p-3 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              >
                {selectedRepoInfo.branches.map((branch) => (
                  <option key={branch} value={branch}>
                    {branch}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Task Description */}
          <div className="space-y-3">
            <label className="text-sm font-medium">Task Description</label>
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="Describe what you want implemented...

Examples: Add user auth • Fix login bug • Implement pagination"
              className="w-full p-3 border rounded-md h-24 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <p className="text-xs text-gray-500">
              Be specific about what you want implemented.
            </p>
          </div>

          {/* Error Display */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            onClick={handleSubmit}
            disabled={loading || !selectedRepo || !selectedBranch || !task.trim()}
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Starting Workflow...
              </>
            ) : (
              'Start Workflow'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}