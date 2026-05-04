import React, { useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import {
  FileText,
  Scan,
  ShieldAlert,
  Sparkles,
  UploadCloud,
  X,
  AlertTriangle,
  CheckCircle2,
  Bot,
  Calendar,
  ShieldCheck,
  HelpCircle,
  FileDown,
  ZoomIn,
  ZoomOut
} from 'lucide-react';
import clsx from 'clsx';
import { twMerge } from 'tailwind-merge';
import confetti from 'canvas-confetti';
import jsPDF from 'jspdf';
import 'jspdf-autotable';
import './App.css';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export default function App() {
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState('');

  const [eli5Mode, setEli5Mode] = useState(false);

  const [riskScore, setRiskScore] = useState(null); // 0..100
  const [riskLevel, setRiskLevel] = useState('—');
  const [keywordsFound, setKeywordsFound] = useState([]);
  const [standardExplanation, setStandardExplanation] = useState('');
  const [eli5Explanation, setEli5Explanation] = useState('');
  const [negotiationTips, setNegotiationTips] = useState([]);
  const [rentalDetails, setRentalDetails] = useState(null);
  const [universalDetails, setUniversalDetails] = useState(null);

  const [checklist, setChecklist] = useState({});
  const [showEmailDraft, setShowEmailDraft] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  const [entities, setEntities] = useState([]);
  const [deadlines, setDeadlines] = useState([]);
  const [counterProposals, setCounterProposals] = useState([]);
  const [negotiationToolkit, setNegotiationToolkit] = useState([]);
  const [signatureChecklist, setSignatureChecklist] = useState({ rera: false, carpet: false, payment: false });
  const [criticalClauses, setCriticalClauses] = useState([]);

  const toggleChecklist = (key) => setChecklist((prev) => ({ ...prev, [key]: !prev[key] }));
  const toggleSignatureChecklist = (key) => setSignatureChecklist((prev) => ({ ...prev, [key]: !prev[key] }));

  const normalizedRisk = useMemo(() => {
    if (typeof riskScore !== 'number' || Number.isNaN(riskScore)) return 0;
    return Math.max(0, Math.min(100, riskScore));
  }, [riskScore]);

  const isHighRisk = useMemo(() => {
    const lvl = String(riskLevel || '').toLowerCase();
    return normalizedRisk >= 75 || lvl.includes('high');
  }, [normalizedRisk, riskLevel]);

  const simplifiedText = useMemo(() => {
    const base = String(eli5Explanation || '').trim();
    if (!base) return '';
    if (eli5Mode) return base;

    // Remove most emoji / pictographs for "simple English" mode without the emoji styling.
    // This keeps words/punctuation intact while making the "Original" vs "Simplified" panes distinct.
    return base
      .replace(/[\p{Extended_Pictographic}\uFE0F]/gu, '')
      .replace(/ {2,}/g, ' ')
      .trim();
  }, [eli5Explanation, eli5Mode]);

  const angle = useMemo(() => {
    // Map 0..100 -> -90..90 (semi-circle)
    return -90 + (normalizedRisk / 100) * 180;
  }, [normalizedRisk]);

  const riskTone = useMemo(() => {
    const lvl = String(riskLevel || '').toLowerCase();
    if (normalizedRisk >= 80 || lvl.includes('high')) return 'high';
    if (normalizedRisk >= 60 || lvl.includes('medium')) return 'medium';
    if (normalizedRisk >= 25 || lvl.includes('low')) return 'low';
    return 'safe';
  }, [normalizedRisk, riskLevel]);

  const riskAccent = useMemo(() => {
    switch (riskTone) {
      case 'high':
        return 'text-rose-300';
      case 'medium':
        return 'text-orange-400';
      case 'low':
        return 'text-emerald-300';
      default:
        return 'text-sky-300';
    }
  }, [riskTone]);

  function resetResults() {
    setError('');
    setRiskScore(null);
    setRiskLevel('—');
    setKeywordsFound([]);
    setStandardExplanation('');
    setEli5Explanation('');
    setNegotiationTips([]);
    setRentalDetails(null);
    setUniversalDetails(null);
    setChecklist({});
    setShowEmailDraft(false);
    setToastMessage('');
    setEntities([]);
    setDeadlines([]);
    setCounterProposals([]);
    setNegotiationToolkit([]);
    setSignatureChecklist({ rera: false, carpet: false, payment: false });
    setCriticalClauses([]);
  }

  function onPickFile(f) {
    if (!f) return;
    setFile(f);
    setError('');
  }

  async function analyze() {
    if (!file) {
      setError('Please upload a PDF or image to scan.');
      return;
    }

    setIsAnalyzing(true);
    setError('');
    resetResults();

    try {
      const form = new FormData();
      form.append('file', file);

      const res = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        body: form,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(text || `Request failed (${res.status})`);
      }

      const data = await res.json();

      if (data?.error) {
        // Backend returns {error: "..."} with 200 in some OCR failure paths.
        setError(String(data.error));
        setToastMessage(String(data.error));
        setTimeout(() => setToastMessage(''), 5000);
        return;
      }

      // Support both schemas:
      // 1) New schema: risk_score, risk_level, standard_explanation, eli5_explanation, keywords_found, negotiation_tips
      // 2) Current backend schema: overall_risk, clauses[], summary, recommendations[]

      const backendRiskLevel = data?.risk_level ?? data?.overall_risk ?? '—';

      let score = data?.risk_score;
      if (typeof score === 'string') score = Number(score);
      // Backend now returns scaled score (e.g. 80). Don't scale it further if it's already >10.
      if (typeof score === 'number' && score <= 1) score = score * 100;
      if (typeof score === 'number' && score > 1 && score <= 10) score = score * 10;

      if (typeof score !== 'number' || Number.isNaN(score)) {
        // Derive score from overall_risk or found clause risk_scores
        const clauses = Array.isArray(data?.clauses) ? data.clauses : [];
        const clauseMax10 = clauses.reduce((m, c) => Math.max(m, Number(c?.risk_score) || 0), 0); // 0..10
        const derivedFromClauses = clauseMax10 ? Math.max(0, Math.min(100, clauseMax10 * 10)) : null;

        const lvl = String(backendRiskLevel || '').toLowerCase();
        const derivedFromLevel = lvl.includes('high') ? 85 : lvl.includes('medium') ? 60 : lvl.includes('low') ? 35 : lvl.includes('safe') ? 15 : 0;

        score = derivedFromClauses ?? derivedFromLevel;
      }

      const clauses = Array.isArray(data?.clauses) ? data.clauses : [];
      const keywords = Array.isArray(data?.keywords_found)
        ? data.keywords_found
        : clauses.map((c) => c?.pattern).filter(Boolean);

      const standardText =
        data?.standard_explanation ??
        data?.summary ??
        (clauses.length
          ? clauses
            .map((c) => `• ${String(c?.standard_explanation ?? '').trim()}`.trim())
            .filter((s) => s.length > 2)
            .join('\n')
          : '');

      const eli5Text =
        data?.eli5_explanation ??
        (clauses.length
          ? clauses
            .map((c) => `• ${String(c?.eli5_translation ?? '').trim()}`.trim())
            .filter((s) => s.length > 2)
            .join('\n')
          : '');

      const tips = Array.isArray(data?.negotiation_tips)
        ? data.negotiation_tips
        : Array.isArray(data?.recommendations)
          ? data.recommendations
          : [];

      const finalScore = typeof score === 'number' && !Number.isNaN(score) ? score : 0;
      setRiskScore(finalScore);
      setRiskLevel(backendRiskLevel);
      setStandardExplanation(String(standardText ?? ''));
      setEli5Explanation(String(eli5Text ?? ''));
      setKeywordsFound(keywords);
      setNegotiationTips(tips.slice(0, 3));
      if (data?.rental_details && Object.keys(data.rental_details).length > 0) {
        setRentalDetails(data.rental_details);
      }
      if (data?.universal_details) {
        setUniversalDetails(data.universal_details);
      }

      if (data.entities) setEntities(data.entities);
      if (data.deadlines) setDeadlines(data.deadlines);
      if (data.counter_proposals) setCounterProposals(data.counter_proposals);
      if (data.negotiation_toolkit) setNegotiationToolkit(data.negotiation_toolkit);
      if (data.critical_clauses) setCriticalClauses(data.critical_clauses);

      console.log('READY: ALL SYSTEMS GO');

      const isSafe = finalScore < 50 && !backendRiskLevel.toLowerCase().includes('high');
      
      const isFair = data?.rental_details?.notice_period?.includes('1') || (!data?.universal_details?.nda_penalty && isSafe && !data?.rental_details?.penalty?.includes('2x'));

      if (isFair || isSafe) {
        confetti({
          particleCount: 150,
          spread: 70,
          origin: { y: 0.6 }
        });
      }

    } catch (e) {
      console.error(e);
      setError('Failed to analyze. Confirm the backend is running and `/analyze` is reachable.');
    } finally {
      setIsAnalyzing(false);
    }
  }

  const highlightText = (text) => {
    if (!text) return '';
    let html = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");

    const rules = [
      { regex: /\b(indemnify|indemnity|indemnification)\b/gi, color: 'font-mono text-red-400 font-bold bg-red-400/10 px-1 rounded text-[1.05em]' },
      { regex: /\b(jurisdiction|governing law)\b/gi, color: 'font-mono text-blue-400 font-bold bg-blue-400/10 px-1 rounded text-[1.05em]' },
      { regex: /\b(liability|breach|termination|arbitration)\b/gi, color: 'font-mono text-amber-400 font-bold bg-amber-400/10 px-1 rounded text-[1.05em]' },
      { regex: /\b(non-compete|perpetuity|critical)\b/gi, color: 'font-mono text-rose-500 font-bold bg-rose-500/10 px-1 rounded text-[1.05em]' }
    ];

    rules.forEach(rule => {
      html = html.replace(rule.regex, (match) => `<span class="${rule.color}">${match}</span>`);
    });

    html = html.replace(/^[•\-\*]\s+(.*)$/gm, '<div class="text-[1.1em] mb-1.5 leading-relaxed">• $1</div>');
    html = html.replace(/⚠️ CRITICAL:/g, '<strong class="text-rose-500 text-[1.1em] font-extrabold animate-pulse">⚠️ CRITICAL:</strong>');

    return <div className="whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: html }} />;
  };

  const highlightAuditText = (text) => {
    if (!text) return '';
    let parts = text.split(/(\.{3,}|_{3,})/g);
    return (
      <span className="body-text">
        {parts.map((part, i) => {
          if (part.match(/^(\.{3,}|_{3,})$/)) {
             return <span key={i} className="bg-rose-500/50 text-rose-200 px-1 rounded-full animate-[pulse_1.5s_ease-in-out_infinite] mx-1" title="Incomplete Section">{part}</span>;
          }
          return <span key={i}>{part}</span>;
        })}
      </span>
    );
  };

  const fairnessVerdict = useMemo(() => {
    const notice = rentalDetails?.notice_period || '';
    if (notice.includes('1 month') || notice.includes('1')) {
      return { label: 'Fair', cls: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' };
    }
    if (universalDetails?.nda_penalty || rentalDetails?.penalty?.includes('2x')) {
      return { label: 'Unfair/Predatory', cls: 'bg-rose-500/10 border-rose-500/20 text-rose-300' };
    }
    if (normalizedRisk >= 75) return { label: 'Unfair/Predatory', cls: 'bg-rose-500/10 border-rose-500/20 text-rose-300' };
    if (normalizedRisk <= 35) return { label: 'Fair', cls: 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' };
    return { label: 'Standard', cls: 'bg-amber-500/10 border-amber-500/20 text-amber-300' };
  }, [rentalDetails, universalDetails, normalizedRisk]);

  const generatePDF = () => {
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.width;
    const pageHeight = doc.internal.pageSize.height;

    const addWatermark = () => {
      doc.setTextColor(240, 240, 240);
      doc.setFontSize(50);
      doc.text('CONFIDENTIAL AUDIT', pageWidth / 2, pageHeight / 2, { angle: 45, align: 'center', baseline: 'middle' });
      doc.setTextColor(0, 0, 0);
    };

    addWatermark();

    doc.setFontSize(24);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(30, 58, 138);
    doc.text('LegalShield AI', 14, 25);
    
    doc.setFontSize(10);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(100, 100, 100);
    const dateStr = new Date().toLocaleDateString();
    doc.text(`Generated on: ${dateStr}`, pageWidth - 14, 25, { align: 'right' });
    
    doc.setLineWidth(0.5);
    doc.line(14, 30, pageWidth - 14, 30);

    doc.setFontSize(16);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 0, 0);
    doc.text('Section 1: Executive Summary', 14, 42);

    doc.setFontSize(12);
    doc.setFont("helvetica", "normal");
    doc.text(`Overall Risk Gauge: ${Math.round(normalizedRisk)}/100 (${riskLevel})`, 14, 52);
    
    doc.setFontSize(11);
    doc.text('Verdict:', 14, 62);
    const splitEli5 = doc.splitTextToSize(simplifiedText || 'No major issues detected. Standard legal provisions apply.', 180);
    doc.setTextColor(50, 50, 50);
    doc.text(splitEli5, 14, 69);

    let nextY = 69 + (splitEli5.length * 5) + 15;

    if (criticalClauses && criticalClauses.length > 0) {
        doc.setFontSize(16);
        doc.setFont("helvetica", "bold");
        doc.setTextColor(0, 0, 0);
        doc.text('Section 2: Highlighted Audit Table', 14, nextY);
        
        const tableData = criticalClauses.map(c => [
            c.title + `\n[${c.status}]`,
            c.original_text,
            c.analysis
        ]);

        doc.autoTable({
            startY: nextY + 5,
            head: [['Clause Category', 'Highlighted Original Text', 'AI Risk Analysis']],
            body: tableData,
            theme: 'grid',
            headStyles: { fillColor: [30, 58, 138], textColor: 255 },
            styles: { fontSize: 10, cellPadding: 4, overflow: 'linebreak' },
            columnStyles: {
                0: { cellWidth: 35, fontStyle: 'bold' },
                1: { cellWidth: 90 },
                2: { cellWidth: 60 }
            },
            willDrawCell: function(data) {
                if (data.section === 'body' && data.column.index === 1) {
                    const doc = data.doc;
                    doc.setFillColor(255, 242, 0); // Bright Yellow highlighter
                    let x = data.cell.x + data.cell.padding('left');
                    let y = data.cell.y + data.cell.padding('top');
                    const fontSize = data.cell.styles.fontSize;
                    const scaleFactor = doc.internal.scaleFactor || 2.834;
                    const lineHeight = (fontSize * 1.15) / scaleFactor;
                    
                    data.cell.text.forEach((line, i) => {
                        if (line.trim() !== '') {
                            let w = doc.getTextWidth(line);
                            doc.rect(x - 1, y + (i * lineHeight) - 0.5, w + 2, lineHeight, 'F');
                        }
                    });
                }
            },
            didParseCell: function(data) {
                if (data.section === 'body' && data.column.index === 1) {
                    data.cell.styles.fillColor = [255, 253, 230]; // Light-yellow background for cell
                    if (data.cell.text.some(t => t.match(/\.{3,}|_{3,}/))) {
                         data.cell.styles.fillColor = [255, 230, 230];
                         data.cell.text.unshift("[INCOMPLETE SECTION DETECTED]");
                    }
                }
                if (data.section === 'body' && data.column.index === 0) {
                    if (data.cell.text[1] && data.cell.text[1].includes('Warning')) {
                         data.cell.styles.textColor = [220, 38, 38];
                    }
                }
            }
        });
        nextY = doc.lastAutoTable.finalY + 15;
    }

    if (nextY > 240) {
        doc.addPage();
        addWatermark();
        nextY = 20;
    }

    doc.setFontSize(16);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(0, 0, 0);
    doc.text('Section 3: Negotiation Scripts', 14, nextY);
    
    let scripts = [];
    if (negotiationToolkit && negotiationToolkit.length > 0) {
        scripts.push(...negotiationToolkit);
    }
    if (counterProposals && counterProposals.length > 0) {
        scripts.push(...counterProposals);
    }
    if (negotiationTips && negotiationTips.length > 0) {
        scripts.push(...negotiationTips);
    }
    
    scripts = [...new Set(scripts)];
    if (scripts.length === 0) scripts.push("Ask for clarification on ambiguous terms and standard indemnities.");

    doc.setFontSize(11);
    doc.setFont("helvetica", "normal");
    doc.setTextColor(50, 50, 50);
    
    nextY += 10;
    scripts.forEach((script) => {
        const lines = doc.splitTextToSize(`• ${script}`, 180);
        
        if (nextY + (lines.length * 5) > 280) {
            doc.addPage();
            addWatermark();
            nextY = 20;
        }
        
        doc.text(lines, 14, nextY);
        nextY += (lines.length * 5) + 3;
    });

    const pageCount = doc.internal.getNumberOfPages();
    for (let i = 2; i <= pageCount; i++) {
        doc.setPage(i);
        doc.setTextColor(240, 240, 240);
        doc.setFontSize(50);
        doc.text('CONFIDENTIAL AUDIT', pageWidth / 2, pageHeight / 2, { angle: 45, align: 'center', baseline: 'middle' });
    }

    doc.save('LegalShield_Audit.pdf');
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } }
  };

  const downloadCalendarInvite = () => {
    let icsContent = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//LegalShield//EN\n";
    deadlines.forEach((dl) => {
      let d = new Date(dl.date);
      if (isNaN(d.getTime())) d = new Date(); // fallback
      
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      const dateStr = `${yyyy}${mm}${dd}`;

      icsContent += "BEGIN:VEVENT\n";
      icsContent += `DTSTART;VALUE=DATE:${dateStr}\n`;
      icsContent += `DTEND;VALUE=DATE:${dateStr}\n`;
      icsContent += `SUMMARY:Legal Deadline - ${dl.context.substring(0, 30)}\n`;
      icsContent += `DESCRIPTION:${dl.context}\n`;
      icsContent += "END:VEVENT\n";
    });
    icsContent += "END:VCALENDAR";

    const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'deadlines.ics';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen w-full bg-[#050505] font-sans text-white overflow-hidden flex items-center justify-center">
      <div style={{ display: 'flex', flexDirection: 'row', alignItems: 'flex-start', gap: '24px', padding: '20px', boxSizing: 'border-box' }} className="h-full w-full max-w-[1300px] mx-auto">
        {toastMessage && (
          <div className="fixed top-6 right-6 z-50 bg-rose-500/90 backdrop-blur-md text-white px-5 py-3 rounded-full shadow-2xl flex items-center gap-3 animate-in fade-in slide-in-from-top-5">
             <AlertTriangle size={20} />
             <span className="font-medium text-sm">{toastMessage}</span>
          </div>
        )}
        
        {/* LEFT COLUMN (PDF) */}
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1.8, height: '92vh', minHeight: '92vh', background: '#111', overflow: 'hidden', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)' }}>
          <div className="h-full flex flex-col p-6 overflow-hidden">
          <header className="flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3">
              <div className="relative grid h-11 w-11 place-items-center rounded-2xl border border-white/10 bg-white/5 shadow-[0_0_0_1px_rgba(255,255,255,0.03),0_20px_60px_-25px_rgba(0,0,0,0.9)]">
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-white/10 to-transparent" />
                <ShieldAlert className="relative text-white" size={22} />
              </div>
              <div className="leading-tight">
                <div className="text-lg font-semibold tracking-tight">LegalShield AI</div>
                <div className="text-xs text-white/50">Obsidian Dashboard • Clause Risk Analyzer</div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className={cn('eli5-shell', eli5Mode && 'eli5-shell--active')}>
                <div className="mr-2 hidden text-xs font-medium text-white/60 md:block">ELI5</div>
                <button
                  type="button"
                  className={cn('eli5-toggle', eli5Mode && 'eli5-toggle--active')}
                  onClick={() => setEli5Mode((v) => !v)}
                  aria-pressed={eli5Mode}
                  aria-label="Toggle ELI5 mode"
                >
                  <motion.span
                    className="eli5-knob"
                    animate={{ x: eli5Mode ? 22 : 0 }}
                    transition={{ type: 'spring', stiffness: 520, damping: 34 }}
                  >
                    {eli5Mode ? '✨' : '⚖️'}
                  </motion.span>
                </button>
              </div>
            </div>
          </header>

          <main className="flex flex-col gap-5 flex-1 h-full overflow-hidden mt-6">
              {/* Card 1: Input / Viewer */}
              {!file ? (
                <motion.section
                  variants={cardVariants}
                  initial="hidden"
                  animate="visible"
                  className="bento-card"
                >
                  <div className="mb-4 flex items-center justify-between">
                    <div>
                      <div className="headline text-sm text-white/80">Upload Document</div>
                      <div className="body-text text-xs">PDF or image. Drag & drop like the reference.</div>
                    </div>
                  </div>

                  <div
                    className={cn(
                      'dropzone',
                      isDragging && 'dropzone--drag'
                    )}
                    onDragOver={(e) => {
                      e.preventDefault();
                      setIsDragging(true);
                    }}
                    onDragLeave={(e) => {
                      e.preventDefault();
                      setIsDragging(false);
                    }}
                    onDrop={(e) => {
                      e.preventDefault();
                      setIsDragging(false);
                      const f = e.dataTransfer.files?.[0];
                      if (f) onPickFile(f);
                    }}
                    onClick={() => fileInputRef.current?.click()}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click();
                    }}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      className="hidden"
                      accept=".pdf,.png,.jpg,.jpeg"
                      onChange={(e) => onPickFile(e.target.files?.[0])}
                    />

                    <div className="absolute inset-0 rounded-[26px] bg-gradient-to-b from-white/[0.08] to-transparent opacity-40" />
                    <div className="absolute inset-0 rounded-[26px] bg-[radial-gradient(circle_at_20%_15%,rgba(59,130,246,0.18),transparent_40%),radial-gradient(circle_at_80%_40%,rgba(245,158,11,0.12),transparent_45%)] opacity-70" />

                    <div className="relative z-10 flex w-full flex-col items-center justify-center gap-4 py-8">
                      <div className="grid h-16 w-16 place-items-center rounded-2xl border border-white/10 bg-white/5">
                        <UploadCloud size={32} className="text-white/80" />
                      </div>
                      <div className="text-center">
                        <div className="headline text-lg tracking-tight">
                          Drop your legal document here
                        </div>
                        <div className="body-text text-sm">
                          or click to browse from your computer
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="text-xs text-rose-300">{error ? error : <span className="text-white/40">Tip: upload a contract PDF for best results.</span>}</div>
                  </div>
                </motion.section>
              ) : (
                <motion.section
                  variants={cardVariants}
                  initial="hidden"
                  animate="visible"
                  className="bento-card flex-1 flex flex-col min-h-0 overflow-hidden"
                  style={{ height: '100%' }}
                >
                  <div className="mb-4 flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-2 text-white/90 overflow-hidden">
                      <FileText size={20} className="shrink-0" />
                      <span className="text-sm font-semibold truncate">{file.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold text-white/70 transition hover:border-white/20 hover:bg-white/10"
                      >
                        Change
                      </button>
                      <button
                        type="button"
                        onClick={analyze}
                        disabled={isAnalyzing}
                        className="inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 py-2 text-xs font-bold text-white transition hover:bg-white/20 disabled:opacity-50"
                      >
                        <Scan size={16} />
                        {isAnalyzing ? 'Scanning...' : 'Scan Now'}
                      </button>
                    </div>
                  </div>

                  <div className="flex-1 min-h-0 rounded-xl bg-white overflow-hidden relative border border-white/10 shadow-2xl">
                    {file.type.includes('pdf') ? (
                      <iframe
                        src={URL.createObjectURL(file)}
                        className="w-full h-full border-none"
                        title="Document Preview"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-[#111]">
                        <img
                          src={URL.createObjectURL(file)}
                          className="max-w-full max-h-full object-contain"
                          alt="Document Preview"
                        />
                      </div>
                    )}
                    
                    {isAnalyzing && (
                      <div className="absolute inset-0 bg-blue-900/20 backdrop-blur-md flex items-center justify-center z-40">
                        <div className="bg-black/80 border border-white/10 text-white px-6 py-3 rounded-full flex items-center gap-3 shadow-2xl">
                          <Scan className="animate-spin text-blue-400" size={20} /> 
                          <span className="font-semibold tracking-wide">Analyzing Clauses...</span>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept=".pdf,.png,.jpg,.jpeg"
                    onChange={(e) => onPickFile(e.target.files?.[0])}
                  />
                </motion.section>
              )}
            </main>
            <footer className="shrink-0 mt-4 w-full border-t border-white/10 pt-4 text-white/60 text-xs text-center flex justify-between body-text">
              <div>LegalShield AI © 2026</div>
              <div className="flex gap-4">
                <a href="#" className="hover:text-white transition">Privacy</a>
                <a href="#" className="hover:text-white transition">Terms</a>
              </div>
            </footer>
          </div>
          </div> {/* END LEFT COLUMN */}

          {/* RIGHT COLUMN (Analysis) */}
          <div style={{ flex: 1, height: '92vh', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '24px', padding: '20px', background: '#000', boxSizing: 'border-box', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)' }} className="custom-scrollbar">

          {/* Card 2: Risk Gauge */}
          <motion.section
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            className="bento-card"
          >
            <div className="mb-3 flex items-start justify-between">
              <div>
                <div className="headline text-sm text-white/80">Risk Gauge</div>
                <div className="body-text text-xs">Animated semi-circle • Smooth needle</div>
              </div>
              <div className={cn('risk-pill rounded-full', `risk-pill--${riskTone}`)}>
                {riskLevel}
              </div>
            </div>

            <div className="relative mt-2 flex items-center justify-center">
              <svg viewBox="0 0 240 140" className="h-[160px] w-full max-w-[360px]">
                <defs>
                  <linearGradient id="riskGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#38bdf8" />
                    <stop offset="30%" stopColor="#34d399" />
                    <stop offset="60%" stopColor="#fbbf24" />
                    <stop offset="100%" stopColor="#fb7185" />
                  </linearGradient>
                  <filter id="glow">
                    <feGaussianBlur stdDeviation="3.5" result="coloredBlur" />
                    <feMerge>
                      <feMergeNode in="coloredBlur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>

                {/* base track */}
                <path
                  d="M 30 120 A 90 90 0 0 1 210 120"
                  fill="none"
                  stroke="rgba(255,255,255,0.08)"
                  strokeWidth="16"
                  strokeLinecap="round"
                />

                {/* colored arc */}
                <path
                  className="gauge-arc"
                  d="M 30 120 A 90 90 0 0 1 210 120"
                  fill="none"
                  stroke="url(#riskGrad)"
                  strokeWidth="16"
                  strokeLinecap="round"
                  filter="url(#glow)"
                  pathLength="100"
                  strokeDasharray="100"
                  strokeDashoffset={100 - normalizedRisk}
                />

                {/* needle pivot */}
                <circle cx="120" cy="120" r="10" fill="rgba(255,255,255,0.92)" />
                <circle cx="120" cy="120" r="14" fill="rgba(0,0,0,0.20)" />
              </svg>

              <motion.div
                className="gauge-needle"
                animate={{ rotate: angle }}
                transition={{ type: 'spring', stiffness: 70, damping: 18 }}
              />
            </div>

            <div className="mt-2 flex items-end justify-between">
              <div>
                <div className="text-xs text-white/50">Score</div>
                <div className={cn('text-3xl font-extrabold tracking-tight', riskAccent)}>
                  {riskScore == null ? '—' : Math.round(normalizedRisk)}
                  <span className="text-base font-semibold text-white/35">/100</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-white/50">Keywords</div>
                <div className="mt-1 flex max-w-[230px] flex-wrap justify-end gap-2">
                  {(keywordsFound?.length ? keywordsFound : ['—']).slice(0, 6).map((k, i) => (
                    <span
                      key={`${k}-${i}`}
                      className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-white/70"
                    >
                      {String(k)}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </motion.section>

          {/* Rental Agreement Details (If Available) */}
          {rentalDetails && (
            <motion.section
              variants={cardVariants}
              initial="hidden"
              animate="visible"
              className="bento-card md:col-span-12 grid grid-cols-1 md:grid-cols-3 gap-4"
            >
              {/* Financials Card */}
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="headline text-sm text-white/80 mb-1">Immediate Monthly Outflow</div>
                <div className="body-text text-xs mb-3">Rent + Maintenance</div>
                <div className="headline text-2xl text-white mb-2">
                  Rs. {rentalDetails.monthly_rent || 'Unknown'}
                </div>
                {rentalDetails.security_deposit && (
                  <div className="body-text text-xs">
                    Deposit: <span className="headline text-white">Rs. {rentalDetails.security_deposit}</span>
                  </div>
                )}
              </div>

              {/* Market Benchmark Card */}
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="headline text-sm text-white/80 mb-3">Market Benchmark</div>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                     <span className="body-text text-xs">Fairness Score</span>
                     <span className={cn('px-3 py-1 rounded-full border text-xs font-bold', fairnessVerdict.cls)}>
                        {fairnessVerdict.label}
                     </span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="body-text">Notice Period</span>
                    <span className="headline">{rentalDetails.notice_period || 'Unknown'}</span>
                  </div>
                  {universalDetails?.nda_penalty && (
                    <div className="flex justify-between items-center text-xs">
                      <span className="body-text">NDA Penalty</span>
                      <span className="text-rose-400 headline">{universalDetails.nda_penalty}</span>
                    </div>
                  )}
                  {rentalDetails?.penalty && (
                    <div className="flex justify-between items-center text-xs">
                      <span className="body-text">Overstay Penalty</span>
                      <span className="text-rose-400 headline">{rentalDetails.penalty}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Before You Sign - Bento Checklist */}
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                <div className="headline text-sm text-white/80 mb-1">Before You Sign</div>
                <div className="body-text text-xs mb-3">Site Visit Checklist (Annexure-I)</div>
                <div className="flex flex-col gap-2">
                  {['fans', 'lights', 'geysers'].map(item => (
                    <label key={item} className="flex items-center gap-3 cursor-pointer group" onClick={(e) => { e.preventDefault(); toggleChecklist(item); }}>
                      <div className={cn(
                        "flex items-center justify-center w-5 h-5 border rounded transition",
                        checklist[item] ? 'border-emerald-500 bg-emerald-500/20' : 'border-white/20 bg-white/5'
                      )}>
                        {checklist[item] && <CheckCircle2 size={12} className="text-emerald-400" />}
                      </div>
                      <span className="text-sm text-white/80 capitalize">{item}: {rentalDetails[item] || '0'}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Obligation Timeline */}
              {(rentalDetails.rent_due_date || rentalDetails.expiry_date || rentalDetails.notice_period) && (
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4 md:col-span-3">
                  <div className="mb-4">
                    <div className="headline text-sm text-white/80">Key Dates & Obligations</div>
                    <div className="body-text text-xs">Vertical Timeline UI</div>
                  </div>
                  <div className="relative border-l border-white/10 ml-4 space-y-6 pb-2">
                    <div className="relative pl-6">
                      <div className="absolute left-[-5px] top-1.5 w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]" />
                      <div className="headline text-sm text-white/90">Rent Due Date</div>
                      <div className="body-text text-xs">{rentalDetails.rent_due_date || 'TBD'}</div>
                    </div>
                    <div className="relative pl-6">
                      <div className="absolute left-[-5px] top-1.5 w-2.5 h-2.5 rounded-full bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.5)]" />
                      <div className="headline text-sm text-white/90">Notice Period Deadline</div>
                      <div className="body-text text-xs">{rentalDetails.notice_period || 'TBD'} prior to moving out</div>
                    </div>
                    <div className="relative pl-6">
                      <div className="absolute left-[-5px] top-1.5 w-2.5 h-2.5 rounded-full bg-rose-400 shadow-[0_0_10px_rgba(244,63,94,0.5)]" />
                      <div className="headline text-sm text-white/90">Expiry Date</div>
                      <div className="body-text text-xs">{rentalDetails.expiry_date || 'TBD'}</div>
                    </div>
                  </div>
                </div>
              )}
            </motion.section>
          )}

          {/* Universal Agreement Details (If Available and Not Rental) */}
          {!rentalDetails && universalDetails && universalDetails.doc_type !== "Real Estate Mode" && (
            <motion.section
              variants={cardVariants}
              initial="hidden"
              animate="visible"
              className="bento-card md:col-span-12 grid grid-cols-1 md:grid-cols-4 gap-4"
            >
              <div className="rounded-2xl border border-white/10 bg-black/20 p-4 col-span-1 md:col-span-4 flex items-center gap-3">
                 <div className="headline text-lg text-white/80">{universalDetails.doc_type} Audit</div>
                 <div className="body-text text-xs px-3 py-1 bg-indigo-500/20 text-indigo-300 rounded-full border border-indigo-500/30">Universal Legal Scanner</div>
              </div>

              <>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="headline text-sm text-white/80 mb-1">Duration / Term</div>
                  <div className="headline text-lg text-white mb-2 truncate" title={universalDetails.duration}>
                    {universalDetails.duration || 'Not Specified'}
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="headline text-sm text-white/80 mb-1">Money / Value</div>
                  <div className="headline text-lg text-white mb-2 truncate" title={universalDetails.money}>
                    {universalDetails.money || 'Not Specified'}
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="headline text-sm text-white/80 mb-1">Termination</div>
                  <div className="headline text-lg text-white mb-2 truncate" title={universalDetails.termination}>
                    {universalDetails.termination || 'Not Specified'}
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="headline text-sm text-white/80 mb-1">Dispute / Law</div>
                  <div className="headline text-lg text-white mb-2 truncate" title={universalDetails.governing_law}>
                    {universalDetails.governing_law || 'Not Specified'}
                  </div>
                </div>
              </>
            </motion.section>
          )}



          {/* Negotiation Bot & Toolkit */}
          {(counterProposals.length > 0 || negotiationToolkit.length > 0) && (
            <motion.section
              variants={cardVariants}
              initial="hidden"
              animate="visible"
              className="bento-card md:col-span-12 grid grid-cols-1 md:grid-cols-2 gap-4 bg-black/40"
            >
              {counterProposals.length > 0 && (
                <div>
                  <div className="headline text-sm text-white/80 mb-4 flex items-center gap-2">
                    <Bot size={18} className="text-indigo-400" />
                    Negotiation Bot: AI Counter-Clauses
                  </div>
                  <div className="space-y-3">
                    {counterProposals.map((cp, idx) => (
                      <div key={idx} className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-4 text-sm text-indigo-100 flex items-start gap-3">
                        <ShieldAlert size={16} className="text-indigo-400 mt-0.5 shrink-0" />
                        <span>{cp}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {negotiationToolkit.length > 0 && (
                <div>
                  <div className="text-sm font-semibold text-white/80 mb-4 flex items-center gap-2">
                    <Sparkles size={18} className="text-amber-400" />
                    The Negotiation Toolkit
                  </div>
                  <div className="space-y-3">
                    {negotiationToolkit.map((msg, idx) => (
                      <div key={idx} className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100 flex items-start gap-3">
                        <span>💡</span>
                        <span>{msg}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.section>
          )}



          {/* Deadlines & Calendar Export */}
          {deadlines.length > 0 && (
            <motion.section
              variants={cardVariants}
              initial="hidden"
              animate="visible"
              className="bento-card md:col-span-12"
            >
              <div className="flex justify-between items-center mb-4">
                <div className="headline text-sm text-white/80">Key Deadlines Detected</div>
                <button
                  onClick={downloadCalendarInvite}
                  className="px-3 py-1.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-bold hover:bg-emerald-500/30 transition flex items-center gap-2"
                >
                  <Calendar size={14} /> Download Calendar Invite
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {deadlines.map((dl, idx) => (
                  <div key={idx} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                    <div className="headline text-lg text-white mb-1">{dl.date}</div>
                    <div className="body-text text-xs truncate" title={dl.context}>{dl.context}</div>
                  </div>
                ))}
              </div>
            </motion.section>
          )}

          {/* Card 6: Document Audit Highlights (Now moved to top or below Risk Gauge) */}
          {criticalClauses && criticalClauses.length > 0 && (
            <motion.section
              variants={cardVariants}
              initial="hidden"
              animate="visible"
              className="bento-card flex flex-col"
            >
              <div className="mb-4">
                <div className="headline text-lg text-white/90 flex items-center gap-2">
                  <Scan size={20} className="text-amber-400" />
                  Document Audit Highlights
                </div>
                <div className="body-text text-xs">Top Critical Clauses Extracted</div>
              </div>
              <div className="flex flex-col gap-4">
                {criticalClauses.map((clause, i) => (
                  <div key={i} className="rounded-2xl border border-white/10 bg-black/20 p-4 relative">
                    <div className="flex justify-between items-start mb-2">
                      <div className="headline text-white/80 text-lg">{clause.title}</div>
                      <div className={cn("px-3 py-1 text-xs rounded-full border uppercase tracking-wider",
                        clause.status === 'Warning' ? "bg-rose-500/20 text-rose-300 border-rose-500/30" :
                        clause.status === 'Caution' ? "bg-amber-500/20 text-amber-300 border-amber-500/30" :
                        "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                      )}>
                        {clause.status}
                      </div>
                    </div>
                    
                    <div className="highlight-glow">
                      {highlightAuditText(clause.original_text)}
                    </div>
                    <div className="body-text text-sm mt-2">
                      <strong className="text-white/90">Our Analysis:</strong> {clause.analysis}
                    </div>
                  </div>
                ))}
              </div>
            </motion.section>
          )}

          {/* Card 3: Analysis split-pane */}
          <motion.section
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            className={cn('bento-card md:col-span-12', isHighRisk && 'risk-pulse')}
          >
            <div className="mb-3 flex items-start justify-between">
              <div>
                <div className="headline text-sm text-white/80">Analysis</div>
                <div className="body-text text-xs">Original text vs. simplified explanation</div>
              </div>
              {isHighRisk ? (
                <div className="inline-flex items-center gap-2 rounded-full border border-rose-500/20 bg-rose-500/10 px-3 py-1 text-xs text-rose-200">
                  <AlertTriangle size={14} />
                  High Risk clause detected
                </div>
              ) : (
                <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/60 body-text">
                  <CheckCircle2 size={14} />
                  No high-risk pulse
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="pane">
                <div className="pane-title">Original Text</div>
                <div className="pane-body custom-scrollbar">
                  {standardExplanation ? highlightText(standardExplanation) : <span className="text-white/35">Upload and scan to view.</span>}
                </div>
              </div>
              <div className={cn("pane transition-all duration-500", (simplifiedText.includes('CRITICAL') || eli5Explanation.includes('CRITICAL')) && "border border-rose-500/50 shadow-[0_0_20px_rgba(244,63,94,0.25)]")}>
                <div className="pane-title flex items-center justify-between">
                  Simplified Text
                  {(simplifiedText.includes('CRITICAL') || eli5Explanation.includes('CRITICAL')) && (
                    <AlertTriangle className="text-rose-500 animate-pulse" size={16} />
                  )}
                </div>
                <div className="pane-body custom-scrollbar text-[1.15em] leading-relaxed font-medium">
                  {simplifiedText ? (
                    highlightText(simplifiedText)
                  ) : eli5Explanation ? (
                    // ELI5 exists but got stripped to empty (rare)
                    <span className="text-white/35">Simplified output is empty after cleanup.</span>
                  ) : (
                    <span className="text-white/35">
                      No simplified text returned. (Tip: your backend populates `eli5_explanation` mainly from matched clauses.)
                    </span>
                  )}
                </div>
              </div>
            </div>
          </motion.section>

          {/* Card 4: Recommendations */}
          <motion.section
            variants={cardVariants}
            initial="hidden"
            animate="visible"
            className="bento-card md:col-span-4"
          >
            <div className="mb-3 flex items-start justify-between">
              <div>
                <div className="headline text-sm text-white/80">Recommendations</div>
                <div className="body-text text-xs">Negotiation script tips (3)</div>
              </div>
              <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] text-white/60 body-text">
                Actionable
              </div>
            </div>

            <div className="space-y-3">
              {(negotiationTips?.length ? negotiationTips : ['Scan a document to generate negotiation tips.']).slice(0, 3).map((tip, i) => (
                <div
                  key={i}
                  className="rec-item cursor-pointer hover:bg-white/10 transition group relative"
                  onClick={() => {
                    navigator.clipboard.writeText(String(tip));
                    alert('Tip copied to clipboard!');
                  }}
                  title="Click to copy"
                >
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 shrink-0 text-emerald-400">
                       <CheckCircle2 size={16} />
                    </div>
                    <div className="body-text pr-16 text-sm">
                      {eli5Mode ? `💬 ${String(tip)} ✅` : String(tip)}
                    </div>
                  </div>
                  <div className="mt-1 opacity-0 group-hover:opacity-100 text-xs font-medium text-indigo-300 transition text-right">
                    Copy
                  </div>
                </div>
              ))}
            </div>
          </motion.section>

          {/* Removed PDF Download and Email Generator section as requested */}
        </div>
      </div>
    </div>
  );
}

// export default App;
