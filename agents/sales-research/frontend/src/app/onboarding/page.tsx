"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useRouter } from "next/navigation";
import { CheckCircle2,
  ChevronRight,
  ChevronLeft,
  Zap,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  saveGlobalICP,
  IdealProfileData,
  setOnboardingComplete,
  getGlobalICP,
  saveSellingProfile,
  getSellingProfile,
} from "@/lib/api";
import { MultiSelect } from "@/components/ui/multi-select";
import {
  LINKEDIN_INDUSTRIES,
  COMPANY_SIZE_OPTIONS,
  REVENUE_OPTIONS,
  JOB_TITLE_OPTIONS,
} from "@/lib/constants";
import { useAuth } from "@/context/auth-context";
import { Spinner } from "@/components/ui/spinner"

// --- Schemas ---

const sellingProfileSchema = z.object({
  company_name: z.string().min(1, "Company Name is required"),
  description: z.string().min(1, "Description is required"),
  primary_product: z.string().min(1, "Primary product name is required"),
  product_description: z.string().min(1, "Product description is required"),
});

const icpFormSchema = z.object({
  industry: z.union([z.string(), z.array(z.string())]),
  company_size: z.union([z.string(), z.array(z.string())]).optional(),
  revenue: z.union([z.string(), z.array(z.string())]).optional(),
  job_title: z.union([z.string(), z.array(z.string())]).optional(),
  value_proposition: z.string().optional(),
});

type SellingProfileValues = z.infer<typeof sellingProfileSchema>;
type IcpFormValues = z.infer<typeof icpFormSchema>;

const STEPS = [
  {
    title: "Brand Identity",
    description: "Tell us about what you sell so we can personalize every research report.",
  },
  {
    title: "Target Market",
    description: "Define your ideal customer so we can calibrate lead discovery and scoring.",
  },
];

export default function OnboardingPage() {
  const router = useRouter();
  const { checkOnboarding } = useAuth();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const sellingForm = useForm<SellingProfileValues>({
    resolver: zodResolver(sellingProfileSchema),
    defaultValues: { company_name: "", description: "", primary_product: "", product_description: "" },
  });

  const icpForm = useForm<IcpFormValues>({
    resolver: zodResolver(icpFormSchema),
    defaultValues: { industry: [], company_size: [], revenue: [], job_title: [], value_proposition: "" },
  });

  useEffect(() => {
    async function checkStatus() {
      try {
        const complete = await checkOnboarding();
        if (complete) { router.push("/"); return; }

        const [existingIcp, existingSelling] = await Promise.all([getGlobalICP(), getSellingProfile()]);

        if (existingSelling && existingSelling.company_name !== "Your Company Name") {
          sellingForm.reset({
            company_name: existingSelling.company_name || "",
            description: existingSelling.description || "",
            primary_product: existingSelling.products?.[0]?.name || "",
            product_description: existingSelling.products?.[0]?.description || "",
          });
        }

        if (existingIcp) {
          icpForm.reset({
            industry: existingIcp.industry || [],
            company_size: existingIcp.company_size || [],
            revenue: existingIcp.revenue || [],
            job_title: Array.isArray(existingIcp.job_title)
              ? existingIcp.job_title
              : existingIcp.job_title
                ? (existingIcp.job_title as string).split(",").map((s) => s.trim()).filter(Boolean)
                : [],
            value_proposition: existingIcp.value_proposition || "",
          });
        }
      } catch (e) {
        console.error("Failed to check status", e);
      } finally {
        setIsChecking(false);
      }
    }
    checkStatus();
  }, []);

  const handleLevel1Submit = async (_values: SellingProfileValues) => setStep(2);

  const handleFinalSubmit = async (icpValues: IcpFormValues) => {
    setIsLoading(true);
    setError(null);
    try {
      const s = sellingForm.getValues();
      await saveSellingProfile({
        company_name: s.company_name,
        description: s.description,
        products: [{ name: s.primary_product, description: s.product_description }],
      });
      await saveGlobalICP(icpValues as IdealProfileData);
      await setOnboardingComplete();
      await checkOnboarding();
      router.push("/");
    } catch {
      setError("Failed to save settings. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <Spinner size="lg" />
      </div>
    );
  }

  const currentStep = STEPS[step - 1];

  return (
    <div className="h-screen overflow-hidden bg-white flex flex-col">

      {/* Progress bar — very top */}
      <div className="h-[3px] w-full bg-zinc-100">
        <div
          className="h-full bg-primary transition-all duration-500 ease-out"
          style={{ width: `${(step / STEPS.length) * 100}%` }}
        />
      </div>

      {/* Header */}
      <header className="flex-shrink-0 flex items-center justify-between px-8 py-4 border-b border-zinc-100">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-primary flex items-center justify-center">
            <Zap className="w-3.5 h-3.5 text-primary-foreground" />
          </div>
          <span className="font-black text-sm tracking-tight">Glial</span>
          <span className="text-zinc-400 text-xs ml-1">by Innovize AI</span>
        </div>

        {/* Step dots */}
        <div className="flex items-center gap-2">
          {STEPS.map((s, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold transition-all ${
                i + 1 < step
                  ? "bg-primary text-primary-foreground"
                  : i + 1 === step
                  ? "border-2 border-primary text-primary"
                  : "border border-zinc-200 text-zinc-400"
              }`}>
                {i + 1 < step ? "✓" : i + 1}
              </div>
              {i < STEPS.length - 1 && (
                <div className={`w-8 h-px transition-colors ${i + 1 < step ? "bg-primary" : "bg-zinc-200"}`} />
              )}
            </div>
          ))}
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 flex flex-col px-6">
        <div className="flex-1 flex items-center justify-center">
        <div className="w-full max-w-lg">

          {/* Step heading */}
          <div className="mb-6">
            <p className="text-[11px] font-bold text-primary uppercase tracking-[0.2em] mb-2">
              Step {step} of {STEPS.length}
            </p>
            <h1 className="text-3xl font-black tracking-tight text-zinc-900 mb-2">
              {currentStep.title}
            </h1>
            <p className="text-sm text-zinc-500 leading-relaxed">{currentStep.description}</p>
          </div>

          {/* ── Step 1: Brand Identity ── */}
          {step === 1 && (
            <Form {...sellingForm}>
              <form onSubmit={sellingForm.handleSubmit(handleLevel1Submit)} className="space-y-4">
                <div className="grid grid-cols-2 gap-5">
                  <FormField
                    control={sellingForm.control}
                    name="company_name"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <Label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest">
                          Company Name
                        </Label>
                        <FormControl>
                          <Input
                            placeholder="Acme Corp"
                            {...field}
                            className="h-11 bg-zinc-50 border-zinc-200 focus-visible:ring-primary"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={sellingForm.control}
                    name="primary_product"
                    render={({ field }) => (
                      <FormItem className="space-y-1.5">
                        <Label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest">
                          Main Product / Service
                        </Label>
                        <FormControl>
                          <Input
                            placeholder="Enterprise Cloud Storage"
                            {...field}
                            className="h-11 bg-zinc-50 border-zinc-200 focus-visible:ring-primary"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <FormField
                  control={sellingForm.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem className="space-y-1.5">
                      <Label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest">
                        Company Bio
                      </Label>
                      <FormControl>
                        <Textarea
                          placeholder="What does your company do at a high level?"
                          className="min-h-[76px] resize-none bg-zinc-50 border-zinc-200 focus-visible:ring-primary"
                          {...field}
                        />
                      </FormControl>
                      <p className="text-[11px] text-zinc-400">Used as context in your research reports.</p>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={sellingForm.control}
                  name="product_description"
                  render={({ field }) => (
                    <FormItem className="space-y-1.5">
                      <Label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest">
                      Value Proposition
                      </Label>
                      <FormControl>
                        <Textarea
                          placeholder="What problem does your product solve?"
                          className="min-h-[76px] resize-none bg-zinc-50 border-zinc-200 focus-visible:ring-primary"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <Button type="submit" className="w-full h-11 font-bold">
                  Continue <ChevronRight className="ml-2 h-4 w-4" />
                </Button>
              </form>
            </Form>
          )}

          {/* ── Step 2: Target Market ── */}
          {step === 2 && (
            <Form {...icpForm}>
              <form onSubmit={icpForm.handleSubmit(handleFinalSubmit)} className="space-y-4">
                <FormField
                  control={icpForm.control}
                  name="industry"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <MultiSelect
                          label="Target Industries"
                          options={LINKEDIN_INDUSTRIES}
                          value={field.value}
                          onChange={field.onChange}
                          placeholder="Search & select industries..."
                          allowCustom
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="grid grid-cols-2 gap-5">
                  <FormField
                    control={icpForm.control}
                    name="company_size"
                    render={({ field }) => (
                      <FormItem>
                        <FormControl>
                          <MultiSelect
                            label="Company Size"
                            options={COMPANY_SIZE_OPTIONS}
                            value={field.value || []}
                            onChange={field.onChange}
                            placeholder="Select sizes..."
                            hideSearch
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={icpForm.control}
                    name="revenue"
                    render={({ field }) => (
                      <FormItem>
                        <FormControl>
                          <MultiSelect
                            label="Annual Revenue"
                            options={REVENUE_OPTIONS}
                            value={field.value || []}
                            onChange={field.onChange}
                            placeholder="Select revenue..."
                            hideSearch
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </div>

                <FormField
                  control={icpForm.control}
                  name="job_title"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <MultiSelect
                          label="Target Job Titles"
                          options={JOB_TITLE_OPTIONS}
                          value={field.value || []}
                          onChange={field.onChange}
                          placeholder="e.g. CTO, VP Engineering..."
                          allowCustom
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={icpForm.control}
                  name="value_proposition"
                  render={({ field }) => (
                    <FormItem className="space-y-1.5">
                      <Label className="text-[11px] font-semibold text-zinc-500 uppercase tracking-widest">
                        Custom Pitch Context{" "}
                        <span className="normal-case font-normal text-zinc-400">(optional)</span>
                      </Label>
                      <FormControl>
                        <Textarea
                          placeholder="Any specific angle you want the AI to take?"
                          className="min-h-[60px] resize-none bg-zinc-50 border-zinc-200 focus-visible:ring-primary"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {error && (
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-rose-50 border border-rose-200">
                    <div className="w-1.5 h-1.5 rounded-full bg-rose-500 flex-shrink-0" />
                    <p className="text-xs text-rose-600">{error}</p>
                  </div>
                )}

                <div className="flex gap-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setStep(1)}
                    className="h-11 px-5 border-zinc-200 text-zinc-600 hover:bg-zinc-50"
                  >
                    <ChevronLeft className="mr-1 h-4 w-4" /> Back
                  </Button>
                  <Button type="submit" className="flex-1 h-11 font-bold" disabled={isLoading}>
                    {isLoading ? (
                      <><Spinner size="md" className="mr-2" /> Finalizing...</>
                    ) : (
                      <><CheckCircle2 className="mr-2 h-4 w-4" /> Complete Setup</>
                    )}
                  </Button>
                </div>
              </form>
            </Form>
          )}

        </div>
        </div>
        <p className="text-center text-zinc-400 text-xs py-4">
          You can update these settings anytime from your dashboard.
        </p>
      </main>
    </div>
  );
}
