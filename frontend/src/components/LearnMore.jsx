import React, { useCallback, useEffect, useRef, useState } from 'react'
import api from '../services/api'
import Icon from './Icons'

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
const STAGE_NAMES = { designing: 'Designing the lesson', writing: 'Writing the narration', rendering: 'Rendering the video' }

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
    <ol className="grid grid-cols-3 gap-2">
      {STAGES.map((stage, i) => {
        const done = current > i
        const active = current === i
        return (
          <li key={stage}>
            <div className={`h-1.5 rounded-full ${done || active ? 'bg-ink' : 'bg-line'}`} />
            <div className={`mt-2 text-sm ${active ? 'font-semibold text-ink' : done ? 'text-ink-2' : 'text-ink-3'}`}>
              {STAGE_NAMES[stage]}
            </div>
          </li>
        )
      })}
    </ol>
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
    <div className="grid gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
      <div>
        <h2 className="display text-[clamp(2.2rem,4.4vw,3.5rem)]">Learn a topic before the match</h2>
        <p className="measure mt-6 text-lg text-ink-2">
          Name any coding topic and we will build a narrated explainer video: a hook, a real-world comparison, how it
          works, an animated walk through the code, and a summary. It is made with Claude and Manim.
        </p>
      </div>

      <div>
        <form
          onSubmit={(e) => { e.preventDefault(); generate() }}
          className="flex flex-col gap-3 sm:flex-row"
        >
          <label htmlFor="learn-topic" className="sr-only">Topic to explain</label>
          <input
            id="learn-topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            maxLength={80}
            placeholder="For example: binary search trees, memoization, two pointers"
            className="field h-12 flex-1"
          />
          <button
            type="submit"
            disabled={submitting || working || !topic.trim()}
            className="btn btn-primary h-12 px-6"
          >
            {working ? 'Generating…' : submitting ? 'Starting…' : 'Generate video'}
          </button>
        </form>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="mr-1 text-sm text-ink-3">{ready.length ? 'Ready to watch:' : 'Try:'}</span>
          {chips.map((v) => (
            <button
              key={v.slug}
              type="button"
              onClick={() => (v.pending ? generate(v.topic) : play(v))}
              disabled={working || submitting}
              className="chip h-8 px-3 text-sm transition-colors hover:border-ink-3 hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
            >
              {v.topic}
            </button>
          ))}
        </div>

        {error && (
          <div role="alert" className="mt-6 flex items-start gap-3 rounded-md border border-tomato-ink/40 bg-tomato/10 p-4 text-sm text-ink">
            <Icon name="alert" size={18} className="mt-0.5 text-tomato-ink" />
            {error}
          </div>
        )}

        {working && (
          <div className="panel mt-6 p-5">
            <div className="mb-4 flex items-baseline justify-between">
              <span className="font-semibold">{job.stage_label}…</span>
              <span className="tnum text-sm text-ink-3">
                {Math.floor(job.elapsed_seconds / 60)}m {job.elapsed_seconds % 60}s
              </span>
            </div>
            <StageTrack status={job.status} />
            <p className="mt-4 text-sm text-ink-3">
              A lesson takes a few minutes to write and render, and the first one also records the voiceover. You can
              keep this page open and carry on reading.
            </p>
          </div>
        )}

        {job?.status === 'failed' && (
          <div role="alert" className="mt-6 rounded-md border border-tomato-ink/40 bg-tomato/10 p-5">
            <div className="font-semibold">Could not generate “{job.topic}”</div>
            <p className="mt-1.5 whitespace-pre-line text-sm text-ink-2">{job.error}</p>
            <button type="button" onClick={() => generate(job.topic)} className="btn btn-secondary btn-sm mt-4">
              Try again
            </button>
          </div>
        )}

        {job?.status === 'ready' && (
          <div className="panel mt-6 overflow-hidden">
            <video
              key={job.slug}
              src={mediaUrl(job.video_url)}
              controls
              autoPlay
              playsInline
              className="aspect-video w-full bg-black"
            />
            <div className="flex items-center justify-between border-t border-line px-4 py-3">
              <span className="text-sm font-semibold">{job.topic}</span>
              <a
                href={mediaUrl(job.video_url)}
                download
                className="inline-flex items-center gap-1.5 text-sm font-medium text-ink-2 hover:text-ink"
              >
                <Icon name="download" size={14} />
                Download mp4
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
