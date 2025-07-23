import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'

serve(async (req) => {
  const body = await req.json()
  const message = body.payload?.payload?.payload?.text
  const phone = body.payload?.sender?.phone
  const date = new Date().toISOString()

  if (message?.includes('|')) {
    const [machine, issue] = message.split('|').map(x => x.trim())

    const { error } = await fetch(`${Deno.env.get("SUPABASE_URL")}/rest/v1/failure_logs`, {
      method: 'POST',
      headers: {
        'apikey': Deno.env.get("SUPABASE_ANON_KEY"),
        'Authorization': `Bearer ${Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        machine,
        issue,
        date,
        operator_phone: phone
      })
    })

    if (error) {
      return new Response(JSON.stringify({ status: 'fail', error }), { status: 500 })
    }

    return new Response(JSON.stringify({ status: 'ok', machine, issue }), { status: 200 })
  }

  return new Response(JSON.stringify({ status: 'ignored', reason: 'bad format' }), { status: 400 })
})
