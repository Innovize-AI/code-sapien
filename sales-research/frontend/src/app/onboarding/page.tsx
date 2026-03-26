"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useRouter } from "next/navigation";
import { Loader2, CheckCircle2 } from "lucide-react";

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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  saveICP,
  IdealProfileData,
  getOnboardingStatus,
  setOnboardingComplete,
  getICP,
} from "@/lib/api";

import { MultiSelect } from "@/components/ui/multi-select";
import { LINKEDIN_INDUSTRIES, COMPANY_SIZE_OPTIONS, REVENUE_OPTIONS, JOB_TITLE_OPTIONS } from "@/lib/constants";

const icpFormSchema = z.object({
  industry: z.union([z.string(), z.array(z.string())]).optional(),
  company_size: z.union([z.string(), z.array(z.string())]).optional(),
  revenue: z.union([z.string(), z.array(z.string())]).optional(),
  job_title: z.union([z.string(), z.array(z.string())]).optional(),
  value_proposition: z.string().optional(),
});

export default function OnboardingPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [isChecking, setIsChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const form = useForm<IdealProfileData>({
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
        const status = await getOnboardingStatus();
        if (status.complete) {
          router.push("/");
          return;
        }

        const existingIcp = await getICP();
        if (existingIcp) {
          form.reset({
            industry: existingIcp.industry || [],
            company_size: existingIcp.company_size || [],
            revenue: existingIcp.revenue || [],
            job_title: Array.isArray(existingIcp.job_title)
              ? existingIcp.job_title
              : (existingIcp.job_title ? (existingIcp.job_title as string).split(",").map(s => s.trim()).filter(Boolean) : []),
            value_proposition: existingIcp.value_proposition || ""
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

  async function onSubmit(values: IdealProfileData) {
    setIsLoading(true);
    setError(null);
    try {
      await saveICP(values);
      await setOnboardingComplete();
      // Redirect to dashboard after saving
      router.push("/");
    } catch (e: any) {
      setError("Failed to save settings. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4 animate-in fade-in duration-700">
      <div className="w-full max-w-2xl">
        <Card className="border-border shadow-2xl bg-card/50 backdrop-blur-sm">
          <CardHeader className="space-y-1">
            <div className="flex items-center gap-2 mb-2">
              <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold shadow-sm">
                1
              </div>
              <span className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
                Onboarding
              </span>
            </div>
            <CardTitle className="text-3xl font-extrabold tracking-tight bg-gradient-to-br from-foreground to-foreground/70 bg-clip-text text-transparent">
              Define Your Ideal Customer Profile
            </CardTitle>
            <CardDescription className="text-base text-muted-foreground/80">
              Tell us about your target audience. We'll use this to calibrate our AI for your specific market.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-8"
              >
                <div className="space-y-6">
                  <FormField
                    control={form.control}
                    name="industry"
                    render={({ field }) => (
                      <FormItem>
                        <FormControl>
                          <MultiSelect
                            label="Target Industries"
                            options={LINKEDIN_INDUSTRIES}
                            value={field.value}
                            onChange={field.onChange}
                            placeholder="Search & select industries (e.g. Computer Software, Marketing...)"
                            allowCustom
                          />
                        </FormControl>
                        <FormDescription>Select all industries that apply to your product.</FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <FormField
                      control={form.control}
                      name="company_size"
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <MultiSelect
                              label="Company Size"
                              options={COMPANY_SIZE_OPTIONS}
                              value={field.value}
                              onChange={field.onChange}
                              placeholder="Select sizes..."
                              hideSearch
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="revenue"
                      render={({ field }) => (
                        <FormItem>
                          <FormControl>
                            <MultiSelect
                              label="Annual Revenue"
                              options={REVENUE_OPTIONS}
                              value={field.value}
                              onChange={field.onChange}
                              placeholder="Select revenue..."
                              hideSearch
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                </div>

                <FormField
                  control={form.control}
                  name="job_title"
                  render={({ field }) => (
                    <FormItem>
                      <FormControl>
                        <MultiSelect
                          label="Target Job Titles"
                          options={JOB_TITLE_OPTIONS}
                          value={field.value}
                          onChange={field.onChange}
                          placeholder="e.g. CTO, VP Engineering..."
                          allowCustom
                        />
                      </FormControl>
                      <FormDescription>
                        Select common titles or type your own and press Enter.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="value_proposition"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Value Proposition (Optional)</FormLabel>
                      <FormControl>
                        <Textarea
                          placeholder="Briefly describe how your product helps these customers..."
                          className="resize-none min-h-[80px]"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {error && <div className="text-red-500 text-sm">{error}</div>}

                <Button type="submit" className="w-full" disabled={isLoading}>
                  {isLoading && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Save & Continue
                </Button>
              </form>
            </Form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
