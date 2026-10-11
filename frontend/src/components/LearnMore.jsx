import React, { useCallback, useEffect, useRef, useState } from 'react'
import api from '../services/api'

// ---------------------------------------------------------------------------
// A render takes minutes, so the flow is: POST a topic, get a slug back
// immediately, then poll until the status is "ready". Topics that have already
// been rendered come back ready on the first response and play instantly.
// ---------------------------------------------------------------------------

const POLL_INTERVAL_MS = 4000

// Shown until the backend reports videos of its own, so the section is never
// an empty box on a fresh install.
const SUGGESTIONS = ['binary search', 'hash tables', 'recursion', 'linked lists']

const STAGES = ['designing', 'writing', 'rendering']

/** Absolute URL for a backend-relative media path.
 *
 *  In development Vite proxies /api, so the path works untouched. In production
 *  VITE_API_URL carries the API origin and the returned path already includes
 *  the /api/v1 prefix, so the prefix is trimmed off the base before joining.
 */
function mediaUrl(path) {
  const base = import.meta.env.VITE_API_URL
  if (!base) return path
  return base.replace(/\/api\/v1\/?$/, '') + path
}

function errorMessage(err) {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (err?.response?.status) return `Request failed (${err.response.status}).`
  return 'Could not reach the server.'
}

function StageTrack({ status }) {
  const current = STAGES.indexOf(status)
  return (
    <div className="flex items-center gap-2">
      {STAGES.map((stage, i) => {
        const done = current > i
        const active = current === i
        return (
          <div
            key={stage}
            className={`h-1.5 flex-1 rounded-full transition-all duration-500 ${
 done
                ? 'bg-blue-500'
                : active
                  ? 'bg-gradient-to-r from-blue-500 to-cyan-400 animate-pulse'
                  : 'bg-white/[0.08]'
            }`}
          />
        )
      })}
    </div>
  )
}

export default function LearnMore() {
  const [topic, setTopic] = useState('')
  const [job, setJob] = useState(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [ready, setReady] = useState([])

  // Guards the poll loop against setting state after unmount, and against a
  // reply for a topic the visitor has already moved on from.
  const activeSlug = useRef(null)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  const loadReady = useCallback(async () => {
    try {
      const { data } = await api.get('/videos')
      if (mounted.current) setReady(data.videos || [])
    } catch {
      // The gallery is a nicety; the generator still works without it.
    }
  }, [])

  useEffect(() => { loadReady() }, [loadReady])

  // Poll while a render is in flight.
  useEffect(() => {
    if (!job || job.status === 'ready' || job.status === 'failed') return

    const slug = job.slug
    const timer = setInterval(async () => {
      try {
        const { data } = await api.get(`/videos/${slug}`)
        if (!mounted.current || activeSlug.current !== slug) return
        setJob(data)
        if (data.status === 'ready') loadReady()
      } catch (err) {
        if (!mounted.current || activeSlug.current !== slug) return
        setJob((prev) => ({ ...prev, status: 'failed', error: errorMessage(err) }))
      }
    }, POLL_INTERVAL_MS)

    return () => clearInterval(timer)
  }, [job, loadReady])

  const generate = useCallback(async (requested) => {
    const value = (requested ?? topic).trim()
    if (!value || submitting) return

    setError('')
    setSubmitting(true)
    setJob(null)
    try {
      const { data } = await api.post('/videos/generate', { topic: value })
      activeSlug.current = data.slug
      setJob(data)
      setTopic(value)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      if (mounted.current) setSubmitting(false)
    }
  }, [topic, submitting])

  const play = useCallback((video) => {
    activeSlug.current = video.slug
    setError('')
    setTopic(video.topic)
    setJob({ ...video, status: 'ready' })
  }, [])

  const working = job && STAGES.includes(job.status)
  const chips = ready.length ? ready : SUGGESTIONS.map((t) => ({ slug: t.replace(/ /g, '-'), topic: t, pending: true }))

  return (
    <div>
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 bg-[#101018] border border-blue-500/20 rounded-full px-4 py-1.5 mb-6">
          <span className="w-2 h-2 rounded-full bg-[#3b82f6]" />
          <span className="text-sm font-medium text-[#60a5fa]">Powered by Claude + Manim</span>
        </div>
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4 tracking-tight">Learn More</h2>
        <p className="text-slate-400 max-w-2xl mx-auto text-lg">
          Name any coding topic and we will build you a narrated explainer video —
          hook, real-world intuition, the mechanism, an animated code trace, and a summary.
        </p>
      </div>

      <div className="max-w-3xl mx-auto">
        {/* ── Topic input ─────────────────────────────────────────────────── */}
        <form
          onSubmit={(e) => { e.preventDefault(); generate() }}
          className="flex flex-col sm:flex-row gap-3 mb-5"
        >
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            maxLength={80}
            placeholder="e.g. binary search trees, memoization, two pointers"
            aria-label="Topic to explain"
            className="flex-1 px-6 py-4 bg-[#0A0A10] border border-white/[0.08] rounded-xl text-white placeholder-slate-500 outline-none transition-all duration-300 focus:border-blue-500/50 focus:shadow-[0_0_25px_rgba(59,130,246,0.15)]"
          />
          <button
            type="submit"
            disabled={submitting || working || !topic.trim()}
            className="px-8 py-4 font-bold text-white rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/30 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {working ? 'Generating…' : submitting ? 'Starting…' : 'Generate Video'}
          </button>
        </form>

        {/* ── Suggested / already-rendered topics ─────────────────────────── */}
        <div className="flex flex-wrap items-center gap-2 mb-8">
          <span className="text-xs text-slate-500 mr-1">
            {ready.length ? 'Ready to watch' : 'Try'}
          </span>
          {chips.map((v) => (
            <button
              key={v.slug}
              type="button"
              onClick={() => (v.pending ? generate(v.topic) : play(v))}
              disabled={working || submitting}
              className="px-3 py-1.5 text-sm rounded-full bg-[#0A0A10] border border-white/[0.07] text-slate-300 transition-all duration-300 hover:border-blue-500/40 hover:text-blue-300 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {v.topic}
            </button>
          ))}
        </div>

        {/* ── Errors from the request itself ──────────────────────────────── */}
        {error && (
          <div className="p-4 mb-6 rounded-xl bg-red-500/[0.07] border border-red-500/20 text-sm text-red-300">
            {error}
          </div>
        )}

        {/* ── Progress ────────────────────────────────────────────────────── */}
        {working && (
          <div className="p-6 rounded-2xl bg-[#0A0A10]/80 border border-white/[0.05]">
            <div className="flex items-baseline justify-between mb-4">
              <span className="text-white font-medium">{job.stage_label}…</span>
              <span className="text-slate-500 text-sm font-mono tabular-nums">
                {Math.floor(job.elapsed_seconds / 60)}m {job.elapsed_seconds % 60}s
              </span>
            </div>
            <StageTrack status={job.status} />
            <p className="text-slate-500 text-sm mt-4 leading-relaxed">
              Writing and rendering a lesson takes several minutes — the first
              pass also synthesises the voiceover. You can leave this open; it
              keeps working while you scroll.
            </p>
          </div>
        )}

        {/* ── Failure reported by the generator ───────────────────────────── */}
        {job?.status === 'failed' && (
          <div className="p-6 rounded-2xl bg-red-500/[0.07] border border-red-500/20">
            <div className="text-red-300 font-medium mb-2">
              Could not generate “{job.topic}”
            </div>
            <p className="text-slate-400 text-sm whitespace-pre-line">{job.error}</p>
            <button
              type="button"
              onClick={() => generate(job.topic)}
              className="mt-4 px-5 py-2 text-sm font-medium rounded-lg border border-white/[0.1] text-slate-300 transition-colors hover:border-blue-500/40 hover:text-blue-300"
            >
              Try again
            </button>
          </div>
        )}

        {/* ── The video ───────────────────────────────────────────────────── */}
        {job?.status === 'ready' && (
          <div className="relative group">
            <div className="absolute -inset-4 bg-gradient-to-r from-blue-600/20 to-cyan-600/20 rounded-3xl blur-2xl pointer-events-none" />
            <div className="relative bg-[#0A0A10] border border-white/[0.07] rounded-2xl overflow-hidden shadow-2xl">
              <video
                key={job.slug}
                src={mediaUrl(job.video_url)}
                controls
                autoPlay
                playsInline
                className="w-full aspect-video bg-black"
              />
              <div className="flex items-center justify-between px-5 py-3 bg-[#101018] border-t border-white/[0.05]">
                <span className="text-white text-sm font-medium">{job.topic}</span>
                <a
                  href={mediaUrl(job.video_url)}
                  download
                  className="text-xs text-slate-400 hover:text-blue-300 transition-colors"
                >
                  Download mp4
                </a>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
