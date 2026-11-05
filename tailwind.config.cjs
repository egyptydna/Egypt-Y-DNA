module.exports={
  content:['./index.html','./*.js'],
  theme:{extend:{
    colors:{primary:'#001736',secondary:'#775a19',background:'#f8f9fa'},
    fontFamily:{headline:['Manrope'],body:['Manrope'],mono:['JetBrains Mono']}
  }},
  plugins:[require('@tailwindcss/forms'),require('@tailwindcss/container-queries')]
};
