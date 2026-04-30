"use client"

import { useState } from "react"
import { useAuth } from "@/context/auth-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, Eye, EyeOff, Zap, BarChart3, Target, Shield } from "lucide-react"

const LOADING_STEPS = [
  "Signing in...",
  "Verifying credentials...",
  "Loading your workspace...",
]

export default function LoginPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState(0)
  const [error, setError] = useState("")
  const { login } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (isLoading) return

    setError("")
    setIsLoading(true)
    setLoadingStep(0)

    const stepTimer1 = setTimeout(() => setLoadingStep(1), 700)
    const stepTimer2 = setTimeout(() => setLoadingStep(2), 1400)

    try {
      await login(email, password)
    } catch (err) {
      clearTimeout(stepTimer1)
      clearTimeout(stepTimer2)
      setError("Invalid email or password. Please try again.")
      setIsLoading(false)
      setLoadingStep(0)
    }
  }

  const features = [
    { icon: Zap, label: "AI-powered lead scoring and research" },
    { icon: BarChart3, label: "Buyer journey intelligence and signals" },
    { icon: Target, label: "Automated outreach sequence builder" },
    { icon: Shield, label: "Competitor intel and audience discovery" },
  ]

  return (
    <div className="flex min-h-screen bg-zinc-950">
      {/* Left panel — brand */}
      <div className="hidden lg:flex lg:w-[55%] flex-col justify-between p-12 relative overflow-hidden">
        {/* Background gradient orbs */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full bg-primary/10 blur-[120px]" />
          <div className="absolute bottom-[-10%] right-[-5%] w-[400px] h-[400px] rounded-full bg-blue-500/8 blur-[100px]" />
        </div>

        <div className="relative z-10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <Zap className="w-4 h-4 text-primary-foreground" />
            </div>
            <div>
              <span className="text-white font-black text-lg tracking-tight">Glial</span>
              <span className="text-zinc-500 text-xs font-medium ml-2">by Innovize AI</span>
            </div>
          </div>
        </div>

        <div className="relative z-10 space-y-10">
          <div className="space-y-4">
            <p className="text-xs font-bold text-primary uppercase tracking-[0.2em]">Revenue Intelligence Platform</p>
            <h1 className="text-5xl font-black text-white leading-[1.1] tracking-tight">
              Know your buyer<br />
              <span className="text-zinc-400">before you reach out.</span>
            </h1>
            <p className="text-zinc-400 text-base leading-relaxed max-w-sm">
              AI research, intent signals, and outreach sequences - built for teams that close on context, not volume.
            </p>
            <p className="text-zinc-600 text-xs">Glial · by Innovize AI</p>
          </div>

          <div className="space-y-4">
            {features.map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-md bg-zinc-800 flex items-center justify-center flex-shrink-0">
                  <Icon className="w-3.5 h-3.5 text-primary" />
                </div>
                <span className="text-zinc-300 text-sm">{label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10">
          <p className="text-zinc-600 text-xs">© 2026 Innovize AI. All rights reserved.</p>
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-6 lg:p-16 bg-white dark:bg-zinc-900">
        <div className="w-full max-w-sm space-y-8">
          {/* Mobile logo */}
          <div className="flex items-center gap-2.5 lg:hidden">
            <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center">
              <Zap className="w-3.5 h-3.5 text-primary-foreground" />
            </div>
            <div>
              <span className="font-black text-base tracking-tight">Glial</span>
              <span className="text-zinc-400 text-xs font-medium ml-1.5">by Innovize AI</span>
            </div>
          </div>

          <div className="space-y-1.5">
            <h2 className="text-2xl font-black tracking-tight text-zinc-900 dark:text-white">
              Sign in
            </h2>
            <p className="text-sm text-zinc-500">
              Enter your credentials to access your workspace.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-xs font-semibold text-zinc-600 dark:text-zinc-400 uppercase tracking-widest">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
                className="h-11 bg-zinc-50 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700 focus-visible:ring-primary"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="text-xs font-semibold text-zinc-600 dark:text-zinc-400 uppercase tracking-widest">
                Password
              </Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={isLoading}
                  className="h-11 pr-10 bg-zinc-50 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700 focus-visible:ring-primary"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800">
                <div className="w-1.5 h-1.5 rounded-full bg-rose-500 flex-shrink-0" />
                <p className="text-xs text-rose-600 dark:text-rose-400">{error}</p>
              </div>
            )}

            <Button
              type="submit"
              className="w-full h-11 font-bold text-sm transition-all"
              disabled={isLoading}
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {LOADING_STEPS[loadingStep]}
                </span>
              ) : (
                "Sign In"
              )}
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
