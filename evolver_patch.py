content = open('/root/FONAR/fon-tarayici/backend/main.py').read()

# _update_evolver fonksiyonunun sonuna, await session.commit()'ten önce ekle
old = '    await session.commit()\n# ─── CLAUDE'

new = '''    # ─── FON KARAKTERİ ───────────────────────────────────────────────────────
    # Yeterli veri varsa fon karakterini hesapla ve kaydet
    if len(prices) >= 60:
        char = {}

        # 1. Mevsimsel analiz — hangi ay ortalama ne kadar kazandırıyor
        monthly_avgs = {}
        for ym, ps in monthly.items():
            if len(ps) >= 15:
                monthly_avgs[ym[-2:]] = round((ps[-1] - ps[0]) / ps[0] * 100, 2)
        if monthly_avgs:
            best_month_num = max(monthly_avgs, key=monthly_avgs.get)
            worst_month_num = min(monthly_avgs, key=monthly_avgs.get)
            month_names = {"01":"Ocak","02":"Şubat","03":"Mart","04":"Nisan","05":"Mayıs",
                          "06":"Haziran","07":"Temmuz","08":"Ağustos","09":"Eylül",
                          "10":"Ekim","11":"Kasım","12":"Aralık"}
            char["best_season"] = f"{month_names.get(best_month_num, best_month_num)}: ort. %{monthly_avgs[best_month_num]:+.1f}"
            char["worst_season"] = f"{month_names.get(worst_month_num, worst_month_num)}: ort. %{monthly_avgs[worst_month_num]:+.1f}"

        # 2. Toparlanma hızı — drawdown'dan çıkış süresi
        recovery_days = []
        in_dd = False
        dd_start = 0
        peak_p = prices[0]
        for i, p in enumerate(prices):
            if p >= peak_p:
                if in_dd:
                    recovery_days.append(i - dd_start)
                    in_dd = False
                peak_p = p
            elif (peak_p - p) / peak_p * 100 > 5 and not in_dd:
                in_dd = True
                dd_start = i
        avg_recovery = round(sum(recovery_days) / len(recovery_days)) if recovery_days else None
        char["avg_recovery_days"] = avg_recovery
        if avg_recovery:
            if avg_recovery <= 10:
                char["recovery_profile"] = "hızlı toparlanıyor (ort. %d gün)" % avg_recovery
            elif avg_recovery <= 30:
                char["recovery_profile"] = "orta hızda toparlanıyor (ort. %d gün)" % avg_recovery
            else:
                char["recovery_profile"] = "yavaş toparlanıyor (ort. %d gün)" % avg_recovery

        # 3. Tutarlılık skoru — pozitif gün oranı + düşük drawdown
        consistency = 0
        if pos_ratio >= 55: consistency += 2
        elif pos_ratio >= 50: consistency += 1
        if max_dd < 10: consistency += 2
        elif max_dd < 20: consistency += 1
        if ann_vol < 20: consistency += 1
        char["consistency_score"] = consistency  # 0-5 arası
        char["consistency_label"] = "yüksek" if consistency >= 4 else "orta" if consistency >= 2 else "düşük"

        # 4. Momentum kalıbı — son 3 aydaki ivme trendi
        if len(prices) >= 90:
            m1 = round((prices[-1] - prices[-22]) / prices[-22] * 100, 2)
            m2 = round((prices[-22] - prices[-44]) / prices[-44] * 100, 2) if len(prices) >= 44 else None
            m3 = round((prices[-44] - prices[-66]) / prices[-66] * 100, 2) if len(prices) >= 66 else None
            char["monthly_momentum"] = [m for m in [m3, m2, m1] if m is not None]
            if m2 is not None:
                if m1 > m2: char["momentum_pattern"] = "ivme kazanıyor"
                elif m1 < m2 * 0.5: char["momentum_pattern"] = "ivme kaybediyor"
                else: char["momentum_pattern"] = "ivme sabit"

        # 5. İnsan dilinde karakter özeti
        summary_parts = []
        total_ret = round((prices[-1] - prices[0]) / prices[0] * 100, 2)
        summary_parts.append(f"{len(prices)} günde %{total_ret:+.1f} toplam getiri")
        if ann_vol > 40: summary_parts.append("yüksek dalgalanmalı")
        elif ann_vol < 15: summary_parts.append("düşük dalgalanmalı")
        else: summary_parts.append("orta dalgalanmalı")
        if avg_recovery: summary_parts.append(f"düşüşten ort. {avg_recovery} günde çıkıyor")
        if char.get("best_season"): summary_parts.append(f"en güçlü dönem {char['best_season']}")
        char["summary"] = ", ".join(summary_parts)

        char_content = json.dumps(char, ensure_ascii=False)

        # Kaydet / güncelle
        char_ex = await session.execute(select(EvolverMemory).where(
            EvolverMemory.fund_code == fund_code,
            EvolverMemory.memory_type == "fund_character"))
        char_rec = char_ex.scalar_one_or_none()
        if char_rec:
            char_rec.content = char_content
            char_rec.occurrence_count += 1
            char_rec.confidence = min(0.99, char_rec.confidence + 0.02)
            char_rec.last_seen = datetime.utcnow()
        else:
            session.add(EvolverMemory(
                fund_code=fund_code,
                memory_type="fund_character",
                content=char_content,
                confidence=0.6,
                snapshot_date=today,
            ))

    await session.commit()
# ─── CLAUDE'''

if old in content:
    content = content.replace(old, new, 1)
    open('/root/FONAR/fon-tarayici/backend/main.py', 'w').write(content)
    print("✅ fund_character eklendi")
else:
    print("❌ bulunamadı")
    # debug
    idx = content.find("await session.commit()")
    print(f"commit konumu: {idx}")
    print(repr(content[idx:idx+50]))
