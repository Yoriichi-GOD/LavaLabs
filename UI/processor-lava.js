(() => {
 const brand=document.querySelector('header .brand');
 function apply(){if(!brand)return;const image=brand.querySelector('img');if(image&&image.getAttribute('src')!=='/logo')image.src='/logo';const words=brand.querySelector('span');if(words&&words.textContent!=='LavaLabs'){words.replaceChildren();const strong=document.createElement('strong');strong.textContent='LavaLabs';words.append(strong);}}
 apply();if(brand)new MutationObserver(apply).observe(brand,{childList:true,subtree:true,attributes:true,attributeFilter:['src']});
 document.title='LavaLabs · Flood processor';
})();
