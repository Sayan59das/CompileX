import React, { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import Logo from '../components/Logo'
import Icon from '../components/Icons'

// Scroll reveal hook
function useScrollReveal() {
  return [useRef(null), true]
}

export default function About() {
  const [techRef, techVisible] = useScrollReveal()
  const [creatorsRef, creatorsVisible] = useScrollReveal()
  const [featuresRef, featuresVisible] = useScrollReveal()

  const techStack = {
    frontend: [
      { name: 'React', color: '#61DAFB', desc: 'UI Library' },
      { name: 'Vite', color: '#646CFF', desc: 'Build Tool' },
      { name: 'Socket.IO', color: '#010101', desc: 'Real-time Communication' },
      { name: 'Tailwind CSS', color: '#06B6D4', desc: 'Styling' },
    ],
    backend: [
      { name: 'FastAPI', color: '#009688', desc: 'Python Web Framework' },
      { name: 'PostgreSQL', color: '#336791', desc: 'Database' },
      { name: 'SQLAlchemy', color: '#D71F00', desc: 'ORM' },
      { name: 'Redis', color: '#DC382D', desc: 'Caching' },
    ],
    ai: [
      { name: 'PyTorch', color: '#EE4C2C', desc: 'Deep Learning' },
      { name: 'Transformers', color: '#FFD21E', desc: 'AI Models' },
      { name: 'Python', color: '#3776AB', desc: 'Programming Language' },
    ],
    devops: [
      { name: 'Docker', color: '#2496ED', desc: 'Containerization' },
      { name: 'Vercel', color: '#000000', desc: 'Frontend Hosting' },
      { name: 'Render', color: '#46E3B7', desc: 'Backend Hosting' },
      { name: 'GitHub', color: '#181717', desc: 'Version Control' },
    ],
  }

  const creators = [
    {
      name: 'Kabir',
      role: 'Co-Creator & Full-Stack Developer',
      contributions: [
        'Backend Architecture',
        'AI Model Integration',
        'Database Design',
        'API Development',
      ],
      gradient: 'from-blue-500 to-cyan-500',
    },
    {
      name: 'Sayan',
      role: 'Co-Creator & Full-Stack Developer',
      contributions: [
        'Frontend Development',
        'Real-time Features',
        'UI/UX Design',
        'DevOps & Deployment',
      ],
      gradient: 'from-cyan-500 to-blue-500',
    },
  ]

  const features = [
    { icon: 'bolt', title: 'Real-time Battles', desc: 'WebSocket-powered live coding competitions' },
    { icon: 'message', title: 'AI-Generated Problems', desc: 'Custom transformer models trained on 2000+ LeetCode problems' },
    { icon: 'layers', title: 'Sandboxed Execution', desc: 'Docker containers for secure code execution' },
    { icon: 'trophy', title: 'Competitive Modes', desc: 'Arena matches, 1v1 duels, and tournaments' },
    { icon: 'bars', title: 'Live Leaderboards', desc: 'Real-time ranking updates during matches' },
    { icon: 'lock', title: 'Secure Authentication', desc: 'JWT-based auth with OAuth support' },
  ]

  return (
    <div className="min-h-screen bg-[#05050A] text-slate-200 relative overflow-hidden">
      {/* Animated background */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl " />
        <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-cyan-500/15 rounded-full blur-3xl " />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-500/10 rounded-full blur-3xl" />
      </div>

      <style>{`
        @keyframes float-slow {
          0%, 100% { transform: translate(0, 0) scale(1); }
          33% { transform: translate(30px, -30px) scale(1.1); }
          66% { transform: translate(-20px, 20px) scale(0.9); }
        }
        @keyframes float-slower {
          0%, 100% { transform: translate(0, 0) scale(1); }
          50% { transform: translate(-40px, 40px) scale(1.15); }
        }
        @keyframes float-orbit {
          0% { transform: rotate(0deg) translateX(100px) rotate(0deg); }
          100% { transform: rotate(360deg) translateX(100px) rotate(-360deg); }
        }
        . { animation: float-slow 20s ease-in-out infinite; }
        . { animation: float-slower 25s ease-in-out infinite; }
        .animate-orbit { animation: float-orbit 30s linear infinite; }
      `}</style>

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 backdrop-blur-xl bg-[#05050A]/80 border-b border-white/[0.05]">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <Logo size={40} className="transition-all duration-300 " />
            <span className="text-xl font-bold text-white tracking-tight transition-all duration-300 group-hover:tracking-wide">CompileX</span>
          </Link>
          <Link to="/" className="px-5 py-2.5 text-sm font-semibold bg-[#3b82f6] hover:bg-[#2563eb] text-white rounded-lg transition-all duration-300 shadow-lg shadow-blue-500/25 hover:shadow-blue-500/50 active:scale-95">
            Back to Home
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6">
        <div className="max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-3 mb-8 ">
            <Logo size={80} className="" />
          </div>
          <h1 className="text-5xl md:text-7xl font-bold mb-6 " style={{ animationDelay: '0.1s' }}>
            <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-cyan-400 bg-clip-text text-transparent ">
              About CompileX
            </span>
          </h1>
          <p className="text-xl md:text-2xl text-slate-400 max-w-3xl mx-auto leading-relaxed " style={{ animationDelay: '0.2s' }}>
            A competitive multiplayer coding platform where developers battle in real-time, powered by AI-generated challenges and cutting-edge technology.
          </p>
        </div>
      </section>

      {/* Tech Stack Section */}
      <section ref={techRef} className="relative py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className={`text-center mb-16 transition-all duration-700 ${techVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">Built With</h2>
            <p className="text-lg text-slate-400">Modern technologies powering CompileX</p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {Object.entries(techStack).map(([category, techs], catIdx) => (
              <div
                key={category}
                className={`glass-panel p-8 transition-all duration-700 ${
                  techVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
                }`}
                style={{ transitionDelay: `${catIdx * 0.1}s` }}
              >
                <h3 className="text-2xl font-bold text-white mb-6 capitalize flex items-center gap-3">
                  <span className="w-2 h-2 rounded-full bg-gradient-to-r from-blue-500 to-cyan-500" />
                  {category}
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {techs.map((tech, idx) => (
                    <div
                      key={tech.name}
                      className="p-4 rounded-xl bg-[#0A0A10] border border-white/[0.05] hover:border-blue-500/30 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/20 group cursor-default"
                    >
                      <div className="w-10 h-10 mb-3 rounded-lg flex items-center justify-center text-base font-bold" style={{ background: `${tech.color}26`, color: ['#010101', '#000000', '#181717'].includes(tech.color) ? '#e2e8f0' : tech.color }}>{tech.name[0]}</div>
                      <div className="font-semibold text-white mb-1 group-hover:text-blue-300 transition-colors">{tech.name}</div>
                      <div className="text-xs text-slate-500">{tech.desc}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Creators Section */}
      <section ref={creatorsRef} className="relative py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className={`text-center mb-16 transition-all duration-700 ${creatorsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">Meet the Creators</h2>
            <p className="text-lg text-slate-400">Equal contributors, equal passion</p>
          </div>

          <div className="grid md:grid-cols-2 gap-8">
            {creators.map((creator, idx) => (
              <div
                key={creator.name}
                className={`relative group transition-all duration-700 ${
 creatorsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
                }`}
                style={{ transitionDelay: `${idx * 0.2}s` }}
              >
                {/* Glow effect */}
                <div className={`absolute -inset-1 bg-gradient-to-r ${creator.gradient} rounded-2xl blur-xl opacity-0 group-hover:opacity-50 transition-opacity duration-500`} />
                
                <div className="relative glass-panel p-8 h-full">
                  {/* Avatar */}
                  <div className="flex items-center gap-6 mb-6">
                    <div className={`w-24 h-24 rounded-full bg-gradient-to-br ${creator.gradient} flex items-center justify-center text-4xl font-bold text-white shadow-lg`}>
                      {creator.name[0]}
                    </div>
                    <div>
                      <h3 className="text-3xl font-bold text-white mb-2 group-hover:text-transparent group-hover:bg-gradient-to-r group-hover:bg-clip-text group-hover:from-blue-400 group-hover:to-cyan-400 transition-all duration-300">
                        {creator.name}
                      </h3>
                      <p className="text-slate-400 font-medium">{creator.role}</p>
                    </div>
                  </div>

                  {/* Contributions */}
                  <div>
                    <h4 className="text-sm font-semibold text-slate-500 mb-3">Key Contributions</h4>
                    <ul className="space-y-2">
                      {creator.contributions.map((contribution, i) => (
                        <li key={i} className="flex items-center gap-3 text-slate-300 group/item hover:text-white transition-colors">
                          <span className={`w-1.5 h-1.5 rounded-full bg-gradient-to-r ${creator.gradient} group-hover/item:scale-150 transition-transform`} />
                          {contribution}
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Equal contribution badge */}
                  <div className="mt-6 pt-6 border-t border-white/[0.05]">
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                      <svg className="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                      </svg>
                      <span className="font-medium">Equal Contributor</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section ref={featuresRef} className="relative py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className={`text-center mb-16 transition-all duration-700 ${featuresVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">Key Features</h2>
            <p className="text-lg text-slate-400">What makes CompileX unique</p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {features.map((feature, idx) => (
              <div
                key={feature.title}
                className={`glass-panel p-8 hover:shadow-2xl hover:shadow-blue-500/20 transition-all duration-500 cursor-default border border-transparent hover:border-blue-500/30 ${
                  featuresVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
                }`}
                style={{ transitionDelay: `${idx * 0.1}s` }}
              >
                <div className="w-12 h-12 mb-5 rounded-xl bg-[#3b82f6]/10 flex items-center justify-center text-blue-400"><Icon name={feature.icon} size={24} /></div>
                <h3 className="text-xl font-bold text-white mb-3">{feature.title}</h3>
                <p className="text-slate-400 leading-relaxed">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <div className="glass-panel p-12 relative overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-cyan-500/10 to-cyan-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <div className="relative z-10">
              <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">Ready to Compete?</h2>
              <p className="text-xl text-slate-400 mb-8">Join thousands of developers in real-time coding battles</p>
              <Link
                to="/register"
                className="inline-flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-bold rounded-xl transition-all duration-300 shadow-xl shadow-blue-500/25 hover:shadow-blue-500/50 active:scale-95 "
              >
                Get Started
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="relative py-8 px-6 border-t border-white/[0.05]">
        <div className="max-w-7xl mx-auto text-center text-slate-500 text-sm">
          <p>© 2026 CompileX. Built by Kabir & Sayan</p>
        </div>
      </footer>
    </div>
  )
}
