---
layout: page
title: "Podcast Generator"
---

<header style="text-align:center; padding:2rem 1rem;">
  <div style="position:absolute; top:1rem; right:1rem;">
    <button onclick="showLang('fr')" style="background:none; border:none; font-size:1.5rem; cursor:pointer;">🇫🇷</button>
    <button onclick="showLang('en')" style="background:none; border:none; font-size:1.5rem; cursor:pointer;">🇬🇧</button>
  </div>
  <h1>Podcast Generator</h1>
  <p id="subtitle">Transformez vos scripts en podcasts multi-voix captivants pour l'éducation et la formation avec les API ElevenLabs ou Gemini</p>
</header>

<section style="max-width:850px; margin:2rem auto; padding:0 1rem;">

<div id="fr">

## Pourquoi l'utiliser ?

Podcast Generator est idéal pour les enseignants, formateurs et créateurs de contenu souhaitant donner vie à leurs scripts grâce à des voix naturelles et immersives. Créez des podcasts engageants sans effort technique.

## Fonctionnalités principales

- Multi-voix réaliste avec intonations naturelles
- Support multilingue automatique
- Parfait pour les cours, tutoriels et contenus pédagogiques
- Expérience immersive et dynamique pour les auditeurs

![Exemple de Podcast Generator](podcast_creator_screenshot.png){: .screenshot }

### 🎧 Écoutez la démo

Un extrait de podcast généré avec Podcast Generator :

<audio controls>
  <source src="sample2-gemini.mp3" type="audio/mpeg">
  Votre navigateur ne supporte pas l'élément audio.
</audio>

[Voir la démo complète ici](who_am_i.html)

<div style="text-align:center; margin-top:2rem;">
  <a href="https://github.com/laurentftech/Podcast_generator" class="cta-button">Découvrir sur GitHub</a>
  ☕ [Offrez-moi un café](https://www.buymeacoffee.com/laurentftech){:target="_blank"}
</div>

</div>

<div id="en" style="display:none;">

## Why use it?

Podcast Generator is perfect for teachers, trainers, and content creators who want to bring their scripts to life with natural and immersive voices. Create engaging podcasts effortlessly using the ElevenLabs or Gemini APIs.

## Main features

- Realistic multi-voice with natural intonation
- Automatic multilingual support
- Perfect for courses, tutorials, and educational content
- Immersive and dynamic experience for listeners

podcast_creator_screenshot.png

### 🎧 Listen to the demo

A podcast excerpt generated with Podcast Generator:

<audio controls>
  <source src="sample2-gemini.mp3" type="audio/mpeg">
  Your browser does not support the audio element.
</audio>

[See the visual demo here](who_am_i.html)

<div style="text-align:center; margin-top:2rem;">
  <a href="https://github.com/laurentftech/Podcast_generator" class="cta-button">Discover on GitHub</a>
  ☕ [Offer me a coffee](https://www.buymeacoffee.com/laurentftech){:target="_blank"}
</div>

</div>

</section>

<footer style="text-align:center; padding:2rem; font-size:0.9rem; color:#888;">
Made with ❤️ and ☕ by LaurentFTech
</footer>

<script>
function showLang(lang) {
    document.getElementById('fr').style.display = (lang === 'fr') ? 'block' : 'none';
    document.getElementById('en').style.display = (lang === 'en') ? 'block' : 'none';
    document.getElementById('subtitle').textContent = (lang === 'fr')
        ? "Transformez vos scripts en podcasts multi-voix captivants pour l'éducation et la formation avec les API ElevenLabs ou Gemini"
        : "Turn your scripts into engaging multi-voice podcasts for education and training using the ElevenLabs or Gemini APIs";
}
</script>
