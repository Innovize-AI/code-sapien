'use client';

import { useState } from 'react';
import Link from 'next/link';
import { CheckCircle, ArrowLeft, ArrowRight, Trophy } from '@phosphor-icons/react';
import { CONSTITUENCIES } from '@/lib/data';

type FormData = {
  name: string;
  dob: string;
  gender: string;
  phone: string;
  email: string;
  village: string;
  district: string;
  state: string;
  constituency: string;
};

const INITIAL: FormData = {
  name: '', dob: '', gender: '', phone: '', email: '',
  village: '', district: '', state: '', constituency: '',
};

declare global {
  interface Window {
    Razorpay: new (opts: RazorpayOptions) => { open: () => void };
  }
}

interface RazorpayOptions {
  key: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  handler: (response: { razorpay_payment_id: string }) => void;
  prefill?: { name?: string; contact?: string; email?: string };
  theme?: { color: string };
}

function loadRazorpay(): Promise<void> {
  return new Promise((resolve) => {
    if (document.getElementById('razorpay-script')) { resolve(); return; }
    const s = document.createElement('script');
    s.id = 'razorpay-script';
    s.src = 'https://checkout.razorpay.com/v1/checkout.js';
    s.onload = () => resolve();
    document.body.appendChild(s);
  });
}

const inputClass = (error?: string) =>
  `w-full bg-card border text-cream text-sm px-4 py-3 focus:outline-none focus:border-accent transition-colors placeholder:text-muted ${
    error ? 'border-red-500' : 'border-border'
  }`;

const labelClass = 'block text-[11px] font-semibold text-muted uppercase tracking-[0.15em] mb-2';

export default function RegisterPage() {
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [form, setForm] = useState<FormData>(INITIAL);
  const [loading, setLoading] = useState(false);
  const [membershipNo, setMembershipNo] = useState('');
  const [errors, setErrors] = useState<Partial<FormData>>({});

  const set = (field: keyof FormData, value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((e) => ({ ...e, [field]: '' }));
  };

  const validateStep1 = () => {
    const e: Partial<FormData> = {};
    if (!form.name.trim()) e.name = 'Required';
    if (!form.dob) e.dob = 'Required';
    if (!form.gender) e.gender = 'Required';
    if (!form.phone || !/^\d{10}$/.test(form.phone)) e.phone = 'Enter a valid 10-digit number';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const validateStep2 = () => {
    const e: Partial<FormData> = {};
    if (!form.village.trim()) e.village = 'Required';
    if (!form.district.trim()) e.district = 'Required';
    if (!form.state.trim()) e.state = 'Required';
    if (!form.constituency) e.constituency = 'Select a constituency';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handlePayment = async () => {
    setLoading(true);
    try {
      await loadRazorpay();
      const key = process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID ?? '';
      if (!key) {
        const no = `KSM-${Date.now().toString().slice(-6)}`;
        setMembershipNo(no);
        setStep(4);
        return;
      }
      const rzp = new window.Razorpay({
        key,
        amount: 10000,
        currency: 'INR',
        name: 'KSM Cricket Academy',
        description: '1-Year Membership',
        prefill: { name: form.name, contact: form.phone, email: form.email },
        theme: { color: '#dc2626' },
        handler: () => {
          const no = `KSM-${Date.now().toString().slice(-6)}`;
          setMembershipNo(no);
          setStep(4);
        },
      });
      rzp.open();
    } finally {
      setLoading(false);
    }
  };

  const constituencyLabel = CONSTITUENCIES.find((c) => c.id === form.constituency)?.name ?? '';

  const steps = ['Personal', 'Location', 'Payment'];

  return (
    <div className="min-h-[100dvh] bg-surface pt-24 pb-16">
      <div className="max-w-lg mx-auto px-4">

        {step < 4 && (
          <div className="mb-10">
            <div className="flex items-center gap-0 mb-3">
              {steps.map((s, i) => (
                <div key={s} className="flex items-center flex-1">
                  <div className={`w-7 h-7 flex items-center justify-center text-xs font-bold shrink-0 transition-colors ${
                    step > i + 1 ? 'bg-accent text-white' :
                    step === i + 1 ? 'bg-accent text-white' : 'bg-border text-muted'
                  }`}>
                    {step > i + 1 ? <CheckCircle size={14} weight="bold" /> : i + 1}
                  </div>
                  {i < steps.length - 1 && (
                    <div className={`h-px flex-1 transition-colors ${step > i + 1 ? 'bg-accent' : 'bg-border'}`} />
                  )}
                </div>
              ))}
            </div>
            <div className="flex justify-between text-[10px] text-muted uppercase tracking-[0.15em]">
              {steps.map((s) => <span key={s}>{s}</span>)}
            </div>
          </div>
        )}

        <div className="bg-elevated border border-border p-8">

          {/* Step 1 */}
          {step === 1 && (
            <>
              <h1 className="font-display font-black text-cream uppercase text-3xl tracking-tight mb-1">
                Personal Details
              </h1>
              <p className="text-muted text-sm mb-8">Tell us about yourself</p>

              <div className="space-y-6">
                <div>
                  <label className={labelClass}>Full Name *</label>
                  <input type="text" value={form.name} onChange={(e) => set('name', e.target.value)}
                    placeholder="Your full name" className={inputClass(errors.name)} />
                  {errors.name && <p className="text-red-400 text-xs mt-1">{errors.name}</p>}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={labelClass}>Date of Birth *</label>
                    <input type="date" value={form.dob} onChange={(e) => set('dob', e.target.value)}
                      className={inputClass(errors.dob)} />
                    {errors.dob && <p className="text-red-400 text-xs mt-1">{errors.dob}</p>}
                  </div>
                  <div>
                    <label className={labelClass}>Gender *</label>
                    <select value={form.gender} onChange={(e) => set('gender', e.target.value)}
                      className={`${inputClass(errors.gender)} bg-card`}>
                      <option value="">Select</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                    </select>
                    {errors.gender && <p className="text-red-400 text-xs mt-1">{errors.gender}</p>}
                  </div>
                </div>

                <div>
                  <label className={labelClass}>Phone Number *</label>
                  <div className="flex">
                    <span className="inline-flex items-center px-3 border border-r-0 border-border bg-subtle text-muted text-sm">
                      +91
                    </span>
                    <input type="tel" value={form.phone}
                      onChange={(e) => set('phone', e.target.value.replace(/\D/g, '').slice(0, 10))}
                      placeholder="10-digit mobile number"
                      className={`flex-1 bg-card border text-cream text-sm px-4 py-3 focus:outline-none focus:border-accent transition-colors placeholder:text-muted ${errors.phone ? 'border-red-500' : 'border-border'}`}
                    />
                  </div>
                  {errors.phone && <p className="text-red-400 text-xs mt-1">{errors.phone}</p>}
                </div>

                <div>
                  <label className={labelClass}>Email <span className="text-muted normal-case tracking-normal font-normal">(optional)</span></label>
                  <input type="email" value={form.email} onChange={(e) => set('email', e.target.value)}
                    placeholder="your@email.com" className={inputClass()} />
                </div>
              </div>

              <button onClick={() => validateStep1() && setStep(2)}
                className="w-full mt-8 bg-accent text-white font-bold text-xs py-4 uppercase tracking-[0.12em] hover:bg-red-700 transition-colors active:scale-[0.98] flex items-center justify-center gap-2">
                Continue <ArrowRight size={14} weight="bold" />
              </button>
            </>
          )}

          {/* Step 2 */}
          {step === 2 && (
            <>
              <h1 className="font-display font-black text-cream uppercase text-3xl tracking-tight mb-1">
                Location
              </h1>
              <p className="text-muted text-sm mb-8">Your village, district, and constituency</p>

              <div className="space-y-6">
                <div>
                  <label className={labelClass}>Village / Town *</label>
                  <input type="text" value={form.village} onChange={(e) => set('village', e.target.value)}
                    placeholder="Your village or town" className={inputClass(errors.village)} />
                  {errors.village && <p className="text-red-400 text-xs mt-1">{errors.village}</p>}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className={labelClass}>District *</label>
                    <input type="text" value={form.district} onChange={(e) => set('district', e.target.value)}
                      placeholder="District" className={inputClass(errors.district)} />
                    {errors.district && <p className="text-red-400 text-xs mt-1">{errors.district}</p>}
                  </div>
                  <div>
                    <label className={labelClass}>State *</label>
                    <input type="text" value={form.state} onChange={(e) => set('state', e.target.value)}
                      placeholder="State" className={inputClass(errors.state)} />
                    {errors.state && <p className="text-red-400 text-xs mt-1">{errors.state}</p>}
                  </div>
                </div>

                <div>
                  <label className={labelClass}>Constituency *</label>
                  <select value={form.constituency} onChange={(e) => set('constituency', e.target.value)}
                    className={`${inputClass(errors.constituency)} bg-card`}>
                    <option value="">Select your constituency</option>
                    {CONSTITUENCIES.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                  {errors.constituency && <p className="text-red-400 text-xs mt-1">{errors.constituency}</p>}
                </div>
              </div>

              <div className="flex gap-3 mt-8">
                <button onClick={() => setStep(1)}
                  className="flex items-center gap-2 border border-border text-muted font-bold text-xs px-6 py-4 uppercase tracking-[0.12em] hover:border-cream hover:text-cream transition-colors">
                  <ArrowLeft size={14} weight="bold" /> Back
                </button>
                <button onClick={() => validateStep2() && setStep(3)}
                  className="flex-1 bg-accent text-white font-bold text-xs py-4 uppercase tracking-[0.12em] hover:bg-red-700 transition-colors active:scale-[0.98] flex items-center justify-center gap-2">
                  Continue <ArrowRight size={14} weight="bold" />
                </button>
              </div>
            </>
          )}

          {/* Step 3 */}
          {step === 3 && (
            <>
              <h1 className="font-display font-black text-cream uppercase text-3xl tracking-tight mb-1">
                Confirm
              </h1>
              <p className="text-muted text-sm mb-8">Review before payment</p>

              <div className="bg-card border border-border p-5 mb-6 space-y-3 text-xs">
                {[
                  ['Name', form.name],
                  ['Phone', `+91 ${form.phone}`],
                  ['Village', form.village],
                  ['District', form.district],
                  ['Constituency', constituencyLabel],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between">
                    <span className="text-muted uppercase tracking-[0.1em]">{label}</span>
                    <span className="text-cream font-medium">{value}</span>
                  </div>
                ))}
              </div>

              <div className="border border-accent p-5 mb-6 flex items-center justify-between">
                <div>
                  <p className="text-cream font-semibold text-sm">Annual Membership</p>
                  <p className="text-muted text-xs mt-0.5">Valid 1 year from registration</p>
                </div>
                <span className="font-display font-black text-accent text-3xl">₹100</span>
              </div>

              <p className="text-muted text-[11px] mb-6 text-center">
                Secure payment via Razorpay. UPI, cards, and net banking accepted.
              </p>

              <div className="flex gap-3">
                <button onClick={() => setStep(2)}
                  className="flex items-center gap-2 border border-border text-muted font-bold text-xs px-6 py-4 uppercase tracking-[0.12em] hover:border-cream hover:text-cream transition-colors">
                  <ArrowLeft size={14} weight="bold" /> Back
                </button>
                <button onClick={handlePayment} disabled={loading}
                  className="flex-1 bg-accent text-white font-bold text-xs py-4 uppercase tracking-[0.12em] hover:bg-red-700 transition-colors active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed">
                  {loading ? 'Processing...' : 'Pay ₹100'}
                </button>
              </div>
            </>
          )}

          {/* Step 4 */}
          {step === 4 && (
            <div className="text-center py-4">
              <div className="w-14 h-14 bg-accent flex items-center justify-center mx-auto mb-6">
                <Trophy size={28} className="text-white" weight="fill" />
              </div>
              <h1 className="font-display font-black text-cream uppercase text-3xl tracking-tight mb-2">
                Welcome to KSM
              </h1>
              <p className="text-muted text-sm mb-8">Your membership is confirmed.</p>

              <div className="bg-card border border-border p-6 mb-8 text-left">
                <p className="text-muted text-[11px] uppercase tracking-[0.15em] mb-2">Membership Number</p>
                <p className="font-display font-black text-accent text-4xl">{membershipNo}</p>
                <p className="text-muted text-xs mt-4 leading-relaxed">
                  Your physical membership card will be issued by your constituency coordinator.
                </p>
              </div>

              <div className="flex flex-col gap-3">
                <Link href="/members"
                  className="block bg-accent text-white font-bold text-xs py-4 uppercase tracking-[0.12em] hover:bg-red-700 transition-colors text-center">
                  View Members
                </Link>
                <Link href="/"
                  className="block border border-border text-muted font-bold text-xs py-4 uppercase tracking-[0.12em] hover:border-cream hover:text-cream transition-colors text-center">
                  Back to Home
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
