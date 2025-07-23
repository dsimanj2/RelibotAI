// Supabase Edge Function: PUBLIC

import { serve } from "https://deno.land/std@0.177.0/http/server.ts";

serve(async (req) => {
  console.log("Webhook triggered");

  const body = await req.json();
  console.log("Received payload:", body);

  return new Response(JSON.stringify({ status: "received" }), {
    headers: { "Content-Type": "application/json" },
    status: 200,
  });
});
