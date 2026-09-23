// Компонент для рекламных блоков AdSense
// Пока пустой, готов для будущей настройки рекламы

function AdBlock({ slot, format = "auto", responsive = true }) {
  const isVertical = format === "vertical"

  return (
    <div
      className="ad-block-container"
      style={{
        minHeight: isVertical ? '600px' : '100px',
        width: isVertical ? '100%' : 'auto'
      }}
    >
      {/* Место для рекламы AdSense */}
      {/*
        Здесь будет размещаться код AdSense после одобрения аккаунта:

        Для вертикальных блоков (sidebar):
        <ins className="adsbygoogle"
          style={{ display: 'block' }}
          data-ad-client="ca-pub-5580777050158333"
          data-ad-slot={slot}
          data-ad-format="vertical"></ins>

        Для обычных блоков:
        <ins className="adsbygoogle"
          style={{ display: 'block' }}
          data-ad-client="ca-pub-5580777050158333"
          data-ad-slot={slot}
          data-ad-format={format}
          data-full-width-responsive={responsive}></ins>

        После вставки кода нужно будет добавить скрипт инициализации:
        useEffect(() => {
          try {
            (window.adsbygoogle = window.adsbygoogle || []).push({});
          } catch (err) {
            console.error('AdSense error:', err);
          }
        }, []);
      */}
    </div>
  )
}

export default AdBlock
