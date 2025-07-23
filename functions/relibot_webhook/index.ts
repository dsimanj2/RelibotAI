// supabase/functions/relibot_webhook/index.ts

// @ts-nocheck
// deno-lint-ignore-file
// deno-fmt-ignore-file
// Supabase Edge Function: PUBLIC

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";

// ✅ Mark this function as public (no auth required)
serve(async (req) => {
  const payload = await req.json();
  console.log("Received WhatsApp message:", payload);

  return new Response(JSON.stringify({ status: "received" }), {
    headers: { "Content-Type": "application/json" },
    status: 200,
  });
});
