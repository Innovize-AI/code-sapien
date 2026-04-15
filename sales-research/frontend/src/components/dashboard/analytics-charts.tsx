"use client";

import React from "react";
import {
    AreaChart,
    Area,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    PieChart,
    Pie,
    Cell,
    Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DashboardAnalytics } from "@/lib/api";
import { format, parseISO } from "date-fns";

const COLORS = ["#10b981", "#f59e0b", "#ef4444", "#3b82f6", "#8b5cf6", "#ec4899"];

interface ChartsProps {
    data: DashboardAnalytics;
}

export function AnalyticsCharts({ data }: ChartsProps) {
    // Format dates for the trend chart
    const trendData = data.daily_trends.map((d) => ({
        ...d,
        formattedDate: format(parseISO(d.date), "MMM d"),
    }));

    // Format lead quality for pie chart
    const qualityData = Object.entries(data.lead_quality).map(([name, value]) => ({
        name,
        value,
    }));

    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 p-3 rounded-xl shadow-xl backdrop-blur-md bg-opacity-80">
                    <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-1">{label}</p>
                    <p className="text-sm font-black text-primary">
                        {payload[0].value} {payload[0].name}
                    </p>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-7">
            {/* 1. Daily Volume Trend */}
            <Card className="col-span-4 overflow-hidden border-none bg-gradient-to-br from-white to-zinc-50/50 dark:from-zinc-900/50 dark:to-zinc-950 shadow-2xl shadow-zinc-200/50 dark:shadow-none ring-1 ring-zinc-200/50 dark:ring-zinc-800/50">
                <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                        <div>
                            <CardTitle className="text-lg font-black italic uppercase tracking-tight">Daily Growth</CardTitle>
                            <p className="text-xs text-muted-foreground font-medium">New profiles identified over the last 30 days</p>
                        </div>
                        <div className="px-3 py-1 bg-primary/10 rounded-full">
                            <span className="text-[10px] font-black text-primary uppercase">Trending Up</span>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="p-0 pt-4">
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={trendData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="var(--primary)" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" className="opacity-[0.05]" />
                                <XAxis
                                    dataKey="formattedDate"
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fontSize: 10, fontWeight: 600 }}
                                    dy={10}
                                />
                                <YAxis
                                    axisLine={false}
                                    tickLine={false}
                                    tick={{ fontSize: 10, fontWeight: 600 }}
                                />
                                <Tooltip content={<CustomTooltip />} />
                                <Area
                                    type="monotone"
                                    dataKey="count"
                                    name="Profiles"
                                    stroke="var(--primary)"
                                    strokeWidth={4}
                                    fillOpacity={1}
                                    fill="url(#colorCount)"
                                    animationDuration={2000}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>

            {/* 2. Lead Quality Distribution */}
            <Card className="col-span-3 overflow-hidden border-none bg-gradient-to-br from-white to-zinc-50/50 dark:from-zinc-900/50 dark:to-zinc-950 shadow-2xl shadow-zinc-200/50 dark:shadow-none ring-1 ring-zinc-200/50 dark:ring-zinc-800/50">
                <CardHeader className="pb-2">
                    <CardTitle className="text-lg font-black italic uppercase tracking-tight">Lead Quality</CardTitle>
                    <p className="text-xs text-muted-foreground font-medium">Distribution of identified leads by AI fit</p>
                </CardHeader>
                <CardContent>
                    <div className="h-[300px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={qualityData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={80}
                                    paddingAngle={8}
                                    dataKey="value"
                                    animationBegin={500}
                                    animationDuration={1500}
                                    stroke="none"
                                >
                                    {qualityData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                                <Legend
                                    verticalAlign="bottom"
                                    align="center"
                                    iconType="circle"
                                    formatter={(value: string) => <span className="text-[10px] font-black uppercase tracking-widest text-zinc-500 ml-1">{value}</span>}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>

            {/* 3. Competitor Breakdown */}
            <Card className="col-span-4 overflow-hidden border-none bg-gradient-to-br from-white to-zinc-50/50 dark:from-zinc-900/50 dark:to-zinc-950 shadow-2xl shadow-zinc-200/50 dark:shadow-none ring-1 ring-zinc-200/50 dark:ring-zinc-800/50">
                <CardHeader className="pb-2">
                    <CardTitle className="text-lg font-black italic uppercase tracking-tight">Competitor Sources</CardTitle>
                    <p className="text-xs text-muted-foreground font-medium">Where your leads are engaging with competitors</p>
                </CardHeader>
                <CardContent>
                    <div className="h-[250px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart
                                layout="vertical"
                                data={data.competitor_breakdown}
                                margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="currentColor" className="opacity-[0.05]" />
                                <XAxis type="number" hide />
                                <YAxis
                                    dataKey="name"
                                    type="category"
                                    axisLine={false}
                                    tickLine={false}
                                    width={100}
                                    tick={{ fontSize: 10, fontWeight: 700, fill: "currentColor" }}
                                />
                                <Tooltip cursor={{ fill: 'transparent' }} content={<CustomTooltip />} />
                                <Bar
                                    dataKey="count"
                                    name="Leads"
                                    fill="var(--primary)"
                                    radius={[0, 4, 4, 0]}
                                    barSize={12}
                                    animationDuration={1500}
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>

            {/* 4. Keyword Discovery */}
            <Card className="col-span-3 overflow-hidden border-none bg-gradient-to-br from-white to-zinc-50/50 dark:from-zinc-900/50 dark:to-zinc-950 shadow-2xl shadow-zinc-200/50 dark:shadow-none ring-1 ring-zinc-200/50 dark:ring-zinc-800/50">
                <CardHeader className="pb-2">
                    <CardTitle className="text-lg font-black italic uppercase tracking-tight">Keyword Discovery</CardTitle>
                    <p className="text-xs text-muted-foreground font-medium">Top performing search keywords</p>
                </CardHeader>
                <CardContent>
                    <div className="h-[250px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart
                                layout="vertical"
                                data={data.keyword_breakdown}
                                margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="currentColor" className="opacity-[0.05]" />
                                <XAxis type="number" hide />
                                <YAxis
                                    dataKey="name"
                                    type="category"
                                    axisLine={false}
                                    tickLine={false}
                                    width={80}
                                    tick={{ fontSize: 10, fontWeight: 700, fill: "currentColor" }}
                                />
                                <Tooltip cursor={{ fill: 'transparent' }} content={<CustomTooltip />} />
                                <Bar
                                    dataKey="count"
                                    name="Leads"
                                    fill="#f59e0b"
                                    radius={[0, 4, 4, 0]}
                                    barSize={12}
                                    animationDuration={1500}
                                />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
