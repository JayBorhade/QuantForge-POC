"use client";

import { motion } from "framer-motion";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const data = Array.from({ length: 30 }, (_, i) => ({
  day: i + 1,
  value: 100000 + Math.sin(i * 0.4) * 8000 + i * 1200 + Math.random() * 2000,
  benchmark: 100000 + i * 800,
}));

export function HeroChart() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay: 0.3, duration: 0.6 }}
      className="glass glow-blue h-[320px] w-full rounded-2xl p-4"
    >
      <div className="mb-2 flex items-center justify-between">
        <div>
          <p className="text-xs text-muted-foreground">Portfolio Performance</p>
          <p className="text-2xl font-bold text-emerald-400">+24.8%</p>
        </div>
        <div className="flex gap-4 text-xs">
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-primary" /> Strategy
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-muted-foreground" /> Benchmark
          </span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height="85%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="day" hide />
          <YAxis hide domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{
              background: "rgba(15,23,42,0.9)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
            }}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#3b82f6"
            fill="url(#colorValue)"
            strokeWidth={2}
          />
          <Area
            type="monotone"
            dataKey="benchmark"
            stroke="#64748b"
            fill="none"
            strokeWidth={1}
            strokeDasharray="4 4"
          />
        </AreaChart>
      </ResponsiveContainer>
    </motion.div>
  );
}
