<script setup>
defineProps({ size: { type: Number, default: 40 } })
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 120 120" fill="none" role="img" aria-label="천둥감자 캐릭터">
    <path d="M51 24c-2-9 0-15 6-20 0 8 3 13 7 16 5-8 12-11 20-10-6 7-8 13-7 18" fill="#6C983E" stroke="#31552F" stroke-width="4" stroke-linejoin="round"/>
    <path d="M59 21c22-4 43 9 49 31 8 29-8 53-37 57-26 5-54-7-59-32C6 51 23 26 59 21Z" fill="#C99A5B" stroke="#563A28" stroke-width="5"/>
    <path d="M23 65c3-20 16-33 35-37" stroke="#E9BE82" stroke-width="6" stroke-linecap="round" opacity=".7"/>
    <ellipse cx="44" cy="66" rx="4" ry="5" fill="#382C25"/>
    <ellipse cx="77" cy="64" rx="4" ry="5" fill="#382C25"/>
    <path d="M52 81c6 6 14 6 20-1" stroke="#382C25" stroke-width="4" stroke-linecap="round"/>
    <ellipse cx="32" cy="77" rx="7" ry="4" fill="#E98F78" opacity=".55"/>
    <ellipse cx="88" cy="75" rx="7" ry="4" fill="#E98F78" opacity=".55"/>
    <path d="m88 20 12-15-3 13 12-3-16 19 3-13-8-1Z" fill="#F2C84B" stroke="#755C1F" stroke-width="2" stroke-linejoin="round"/>
    <circle cx="33" cy="46" r="3" fill="#A87A4C"/>
    <circle cx="90" cy="48" r="2.5" fill="#A87A4C"/>
    <circle cx="64" cy="96" r="2" fill="#A87A4C"/>
  </svg>
</template>
