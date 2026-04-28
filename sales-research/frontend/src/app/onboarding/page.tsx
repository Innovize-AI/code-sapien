"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useRouter } from "next/navigation";
import { Loader2, CheckCircle2, ChevronRight, ChevronLeft, Building2, Target, Send } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  saveGlobalICP,
  IdealProfileData,
  setOnboardingComplete,
  getGlobalICP,
  saveSellingProfile,
  getSellingProfile,
  SellingProfileConfig,
} from "@/lib/api";

import { MultiSelect } from "@/components/ui/multi-select";
import {
  LINKEDIN_INDUSTRIES,
  COMPANY_SIZE_OPTIONS,
  REVENUE_OPTIONS,
  JOB_TITLE_OPTIONS,
} from "@/lib/constants";
import { useAuth } from "@/context/auth-context";

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
  job_title: z.union([z.string(), z.array(z.string())]),
  value_proposition: z.string().optional(),
});

type SellingProfileValues = z.infer<typeof sellingProfileSchema>;

export default function OnboardingPage() {
  const router = useRouter();
  const { checkOnboarding } = useAuth();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Forms
  const sellingForm = useForm<SellingProfileValues>({
    resolver: zodResolver(sellingProfileSchema),
    defaultValues: {
      company_name: "",
      description: "",
      primary_product: "",
      product_description: "",
    },
  });

  const icpForm = useForm<IdealProfileData>({
    resolver: zodResolver(icpFormSchema),
    defaultValues: {
      industry: [],
      company_size: [],
      revenue: [],
      job_title: "",
      value_proposition: "",
    },
  });

  useEffect(() => {
    async function checkStatus() {
      try {
        const complete = await checkOnboarding();
        if (complete) {
          router.push("/");
          return;
        }

        const [existingIcp, existingSelling] = await Promise.all([
          getGlobalICP(),
          getSellingProfile()
        ]);

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
                ? (existingIcp.job_title as string)
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean)
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

  const nextStep = () => setStep(step + 1);
  const prevStep = () => setStep(step - 1);

  const handleLevel1Submit = async (values: SellingProfileValues) => {
    nextStep();
  };

  const handleFinalSubmit = async (icpValues: IdealProfileData) => {
    setIsLoading(true);
    setError(null);
    try {
      const sellingValues = sellingForm.getValues();
      
      // 1. Save Selling Profile
      await saveSellingProfile({
        company_name: sellingValues.company_name,
        description: sellingValues.description,
        products: [
          {
            name: sellingValues.primary_product,
            description: sellingValues.product_description,
          }
        ]
      });

      // 2. Save ICP
      await saveGlobalICP(icpValues);
      
      // 3. Mark Complete
      await setOnboardingComplete();
      
      // 4. Update Context & Redirect
      await checkOnboarding();
      router.push("/");
    } catch (e: any) {
      setError("Failed to save settings. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4 animate-in fade-in duration-700">
      <div className="w-full max-w-3xl">
        <Card className="border-border shadow-2xl bg-card/50 backdrop-blur-sm overflow-hidden">
          <div className="h-1.5 w-full bg-muted">
            <div 
              className="h-full bg-primary transition-all duration-500 ease-out" 
              style={{ width: `${(step / 2) * 100}%` }}
            />
          </div>
          
          <CardHeader className="space-y-1">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className={`h-8 w-8 rounded-full flex items-center justify-center font-bold shadow-sm transition-colors ${step === 1 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
                  1
                </div>
                <div className="w-4 h-0.5 bg-muted" />
                <div className={`h-8 w-8 rounded-full flex items-center justify-center font-bold shadow-sm transition-colors ${step === 2 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
                  2
                </div>
              </div>
              <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest bg-muted/50 px-2 py-1 rounded">
                Step {step} of 2
              </span>
            </div>
            
            <CardTitle className="text-3xl font-extrabold tracking-tight bg-gradient-to-br from-foreground to-foreground/70 bg-clip-text text-transparent">
              {step === 1 ? "Brand Identity" : "Target Market"}
            </CardTitle>
            <CardDescription className="text-base text-muted-foreground/80">
              {step === 1 
                ? "First, tell us about what you sell so we can personalize your research reports."
                : "Now, define your ideal customer profile to calibrate our lead discovery AI."}
            </CardDescription>
          </CardHeader>

          <CardContent className="pt-4">
            {step === 1 ? (
              <Form {...sellingForm}>
                <form onSubmit={sellingForm.handleSubmit(handleLevel1Submit)} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <FormField
                      control={sellingForm.control}
                      name="company_name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Company Name</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g. Acme Corp" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={sellingForm.control}
                      name="primary_product"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Main Product/Service</FormLabel>
                          <FormControl>
                            <Input placeholder="e.g. Enterprise Cloud Storage" {...field} />
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
                      <FormItem>
                        <FormLabel>Company Bio</FormLabel>
                        <FormControl>
                          <Textarea 
                            placeholder="What does your company do at a high level?" 
                            className="min-h-[80px]"
                            {...field} 
                          />
                        </FormControl>
                        <FormDescription>Used for the context of your research reports.</FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={sellingForm.control}
                    name="product_description"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Product Value Prop</FormLabel>
                        <FormControl>
                          <Textarea 
                            placeholder="What problem does your product solve?" 
                            className="min-h-[80px]"
                            {...field} 
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="pt-4">
                    <Button type="submit" className="w-full h-12 text-lg">
                      Next Step <ChevronRight className="ml-2 h-5 w-5" />
                    </Button>
                  </div>
                </form>
              </Form>
            ) : (
              <Form {...icpForm}>
                <form onSubmit={icpForm.handleSubmit(handleFinalSubmit)} className="space-y-6">
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

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                            value={field.value}
                            onChange={field.onChange}
                            placeholder="e.g. CTO, VP Sales..."
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
                      <FormItem>
                        <FormLabel>Custom Pitch Context (Optional)</FormLabel>
                        <FormControl>
                          <Textarea
                            placeholder="Any specific angle you want the AI to take?"
                            className="min-h-[80px]"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  {error && <div className="text-red-500 text-sm">{error}</div>}

                  <div className="flex gap-4 pt-4">
                    <Button type="button" variant="outline" onClick={prevStep} className="flex-1 h-12">
                      <ChevronLeft className="mr-2 h-5 w-5" /> Back
                    </Button>
                    <Button type="submit" className="flex-[2] h-12 text-lg" disabled={isLoading}>
                      {isLoading ? (
                        <>
                          <Loader2 className="mr-2 h-5 w-5 animate-spin" /> Finalizing...
                        </>
                      ) : (
                        <>
                          Complete Setup <CheckCircle2 className="ml-2 h-5 w-5" />
                        </>
                      )}
                    </Button>
                  </div>
                </form>
              </Form>
            )}
          </CardContent>
        </Card>
        
        <p className="text-center text-muted-foreground text-xs mt-6">
          You can always update these settings later in your profile dashboard.
        </p>
      </div>
    </div>
  );
}
