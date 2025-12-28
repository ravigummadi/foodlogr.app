import { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL || ''

interface RegistrationResult {
  api_key: string
  message: string
  claude_command: string
}

function App() {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RegistrationResult | null>(null)
  const [copied, setCopied] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Registration failed')
      }

      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
    } finally {
      setIsLoading(false)
    }
  }

  const copyToClipboard = async (text: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100">
      <div className="max-w-4xl mx-auto px-4 py-16">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">
            FoodLogr
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Track your food and macros with Claude AI.
            Persistent logging that syncs across all your conversations.
          </p>
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="text-3xl mb-3">🍎</div>
            <h3 className="font-semibold text-gray-900 mb-2">Log Food Naturally</h3>
            <p className="text-gray-600 text-sm">
              Just tell Claude what you ate. It handles the macro calculations.
            </p>
          </div>
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="text-3xl mb-3">📊</div>
            <h3 className="font-semibold text-gray-900 mb-2">Track Progress</h3>
            <p className="text-gray-600 text-sm">
              Daily summaries and weekly reports with caloric balance tracking.
            </p>
          </div>
          <div className="bg-white rounded-xl p-6 shadow-sm">
            <div className="text-3xl mb-3">🔄</div>
            <h3 className="font-semibold text-gray-900 mb-2">Persistent Memory</h3>
            <p className="text-gray-600 text-sm">
              Your data persists across sessions. Claude remembers your foods.
            </p>
          </div>
        </div>

        {/* Registration Form */}
        {!result ? (
          <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md mx-auto">
            <h2 className="text-2xl font-bold text-gray-900 mb-6 text-center">
              Get Started
            </h2>

            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                  Email address
                </label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="w-full px-4 py-3 rounded-lg border border-gray-300 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition"
                />
              </div>

              {error && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Creating account...' : 'Get API Key'}
              </button>
            </form>
          </div>
        ) : (
          /* Success State */
          <div className="bg-white rounded-2xl shadow-lg p-8 max-w-2xl mx-auto">
            <div className="text-center mb-6">
              <div className="text-5xl mb-4">🎉</div>
              <h2 className="text-2xl font-bold text-gray-900">You're all set!</h2>
              <p className="text-gray-600 mt-2">{result.message}</p>
            </div>

            {/* API Key Display */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Your API Key
              </label>
              <div className="flex gap-2">
                <code className="flex-1 px-4 py-3 bg-gray-100 rounded-lg font-mono text-sm break-all">
                  {result.api_key}
                </code>
                <button
                  onClick={() => copyToClipboard(result.api_key)}
                  className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg text-sm font-medium transition"
                >
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <p className="text-xs text-amber-600 mt-2">
                Save this key securely - it won't be shown again!
              </p>
            </div>

            {/* Claude CLI Command */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Run this in your terminal to connect Claude:
              </label>
              <div className="relative">
                <pre className="px-4 py-3 bg-gray-900 text-gray-100 rounded-lg font-mono text-xs overflow-x-auto">
                  {result.claude_command}
                </pre>
                <button
                  onClick={() => copyToClipboard(result.claude_command)}
                  className="absolute top-2 right-2 px-3 py-1 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded text-xs transition"
                >
                  Copy
                </button>
              </div>
            </div>

            {/* Quick Start */}
            <div className="border-t pt-6">
              <h3 className="font-semibold text-gray-900 mb-3">Quick Start</h3>
              <ol className="space-y-2 text-sm text-gray-600">
                <li>1. Run the command above to add FoodLogr to Claude</li>
                <li>2. Start a new Claude conversation</li>
                <li>3. Say: "Set up my food goals: 2000 cal, 150g protein, 200g carbs, 1800 resting energy"</li>
                <li>4. Then: "I had a cappuccino with 2% milk"</li>
              </ol>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-12 text-gray-500 text-sm">
          <p>FoodLogr uses Claude MCP for seamless AI integration</p>
        </div>
      </div>
    </div>
  )
}

export default App
