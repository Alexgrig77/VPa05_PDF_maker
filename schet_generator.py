#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор счетов в PDF - улучшенная версия
Автоматическая генерация счетов с счетчиком номеров
"""

import os
import json
import pandas as pd
from pathlib import Path
import platform
import subprocess
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Попробуем импортировать WeasyPrint, если не получится - используем альтернативу
WEASYPRINT_AVAILABLE = False
try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except ImportError:
    pass
except Exception:
    pass

REPORTLAB_AVAILABLE = False
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    pass


class SchetGenerator:
    def __init__(self):
        self.data_dir = Path("data")
        self.templates_dir = Path("templates")
        self.output_dir = Path("output")
        
        # Создаем директории если их нет
        self.data_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # Файл для хранения счетчика
        self.counter_file = Path("invoice_counter.json")
        
        # CSS стили для поддержки кириллицы
        self.css_styles = """
        @page {
            size: A4;
            margin: 2cm;
        }
        
        body {
            font-family: 'DejaVu Sans', 'Roboto', Arial, sans-serif;
            font-size: 12px;
            line-height: 1.4;
            color: #333;
        }
        """

    def get_next_invoice_number(self) -> str:
        """Получает следующий номер счета"""
        try:
            if self.counter_file.exists():
                with open(self.counter_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    counter = data.get('counter', 0)
            else:
                counter = 0
            
            counter += 1
            
            # Сохраняем обновленный счетчик
            with open(self.counter_file, 'w', encoding='utf-8') as f:
                json.dump({'counter': counter}, f, ensure_ascii=False, indent=2)
            
            return f"СЧ-{counter:03d}"
            
        except Exception as e:
            print(f"⚠ Ошибка при работе со счетчиком: {e}")
            # Используем временный номер на основе даты
            now = datetime.now()
            return f"СЧ-{now.strftime('%Y%m%d%H%M')}"

    def get_data_files(self) -> List[Path]:
        """Получает список всех CSV и JSON файлов в директории data"""
        data_files = []
        
        # Ищем CSV файлы
        csv_files = list(self.data_dir.glob("*.csv"))
        data_files.extend(csv_files)
        
        # Ищем JSON файлы
        json_files = list(self.data_dir.glob("*.json"))
        data_files.extend(json_files)
        
        return sorted(data_files)

    def get_template_files(self) -> List[Path]:
        """Получает список всех HTML шаблонов в директории templates"""
        template_files = list(self.templates_dir.glob("*.html"))
        return sorted(template_files)

    def read_csv_file(self, file_path: Path) -> pd.DataFrame:
        """Читает CSV файл с помощью pandas"""
        try:
            # Пробуем разные кодировки
            encodings = ['utf-8', 'cp1251', 'latin1']
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    print(f"✓ CSV файл прочитан с кодировкой: {encoding}")
                    return df
                except UnicodeDecodeError:
                    continue
            
            # Если ничего не сработало, используем utf-8 с ошибками
            df = pd.read_csv(file_path, encoding='utf-8', errors='ignore')
            print("⚠ CSV файл прочитан с игнорированием ошибок кодировки")
            return df
            
        except Exception as e:
            print(f"❌ Ошибка при чтении CSV файла: {e}")
            return pd.DataFrame()

    def get_available_invoices(self, data: pd.DataFrame) -> List[str]:
        """Получает список доступных номеров счетов из данных"""
        if 'номер_счета' in data.columns:
            invoices = sorted(data['номер_счета'].unique())
        elif 'invoice_id' in data.columns:
            invoices = sorted(data['invoice_id'].unique())
        else:
            # Ищем колонку с номером счета
            invoice_columns = [col for col in data.columns if 'счет' in col.lower() or 'invoice' in col.lower()]
            if invoice_columns:
                invoices = sorted(data[invoice_columns[0]].unique())
            else:
                invoices = []
        
        return invoices

    def filter_data_by_invoice(self, data: pd.DataFrame, invoice_number: str) -> pd.DataFrame:
        """Фильтрует данные по номеру счета"""
        if 'номер_счета' in data.columns:
            return data[data['номер_счета'] == invoice_number]
        elif 'invoice_id' in data.columns:
            return data[data['invoice_id'] == invoice_number]
        else:
            # Ищем колонку с номером счета
            invoice_columns = [col for col in data.columns if 'счет' in col.lower() or 'invoice' in col.lower()]
            if invoice_columns:
                return data[data[invoice_columns[0]] == invoice_number]
            else:
                return data

    def calculate_totals(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Вычисляет итоговые суммы"""
        totals = {}
        
        if not data.empty:
            # Общая сумма
            if 'общая_сумма' in data.columns:
                totals['общая_сумма'] = data['общая_сумма'].sum()
            elif 'total' in data.columns:
                totals['общая_сумма'] = data['total'].sum()
            else:
                totals['общая_сумма'] = 0
            
            # Количество позиций
            totals['количество_позиций'] = len(data)
            
            # Статус счета
            if 'статус' in data.columns:
                status = data['статус'].iloc[0]
                totals['статус'] = status
                totals['статус_класс'] = 'status-paid' if 'оплачен' in status.lower() else 'status-pending'
            else:
                totals['статус'] = 'Ожидает оплаты'
                totals['статус_класс'] = 'status-pending'
        
        return totals

    def render_template(self, template_path: Path, data: pd.DataFrame, invoice_number: str) -> str:
        """Рендерит HTML шаблон с данными"""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Вычисляем итоги
            totals = self.calculate_totals(data)
            
            # Получаем данные первого ряда для общей информации
            first_row = data.iloc[0] if not data.empty else {}
            
            # Заменяем плейсхолдеры
            html_content = template_content
            
            # Основные плейсхолдеры
            html_content = html_content.replace('{{номер_счета}}', str(invoice_number))
            html_content = html_content.replace('{{дата}}', str(first_row.get('дата', datetime.now().strftime('%Y-%m-%d'))))
            html_content = html_content.replace('{{клиент}}', str(first_row.get('клиент', 'Не указан')))
            html_content = html_content.replace('{{css_styles}}', self.css_styles)
            
            # Вычисляем срок оплаты (дата + 10 дней)
            try:
                invoice_date = datetime.strptime(str(first_row.get('дата', datetime.now().strftime('%Y-%m-%d'))), '%Y-%m-%d')
                due_date = invoice_date + timedelta(days=10)
                html_content = html_content.replace('{{срок_оплаты}}', due_date.strftime('%Y-%m-%d'))
            except:
                html_content = html_content.replace('{{срок_оплаты}}', datetime.now().strftime('%Y-%m-%d'))
            
            # Статус
            html_content = html_content.replace('{{статус}}', totals.get('статус', 'Ожидает оплаты'))
            html_content = html_content.replace('{{статус_класс}}', totals.get('статус_класс', 'status-pending'))
            
            # Общая сумма
            html_content = html_content.replace('{{общая_сумма}}', f"{totals.get('общая_сумма', 0):,.2f}")
            
            # Создаем таблицу товаров
            if not data.empty:
                # Подготавливаем данные для таблицы
                table_data = [['№', 'Товар', 'Количество', 'Цена за ед.', 'Сумма']]
                
                for i, (_, row) in enumerate(data.iterrows(), 1):
                    table_data.append([
                        str(i),
                        str(row.get('товар', '')),
                        str(row.get('количество', '')),
                        f"{row.get('цена_за_единицу', 0):,.2f}",
                        f"{row.get('общая_сумма', 0):,.2f}"
                    ])
                
                # Создаем HTML таблицу
                table_html = '<table class="items-table">'
                
                # Заголовок
                table_html += '<thead><tr>'
                for header in table_data[0]:
                    table_html += f'<th>{header}</th>'
                table_html += '</tr></thead>'
                
                # Тело таблицы
                table_html += '<tbody>'
                for row in table_data[1:]:
                    table_html += '<tr>'
                    for cell in row:
                        table_html += f'<td>{cell}</td>'
                    table_html += '</tr>'
                table_html += '</tbody>'
                
                table_html += '</table>'
                
                html_content = html_content.replace('{{data_table}}', table_html)
            else:
                html_content = html_content.replace('{{data_table}}', '<p>Данные не найдены</p>')
            
            return html_content
            
        except Exception as e:
            print(f"❌ Ошибка при рендеринге шаблона: {e}")
            return ""

    def generate_pdf(self, html_content: str, output_path: Path, data: pd.DataFrame, invoice_number: str) -> bool:
        """Генерирует PDF из HTML контента или данных"""
        if WEASYPRINT_AVAILABLE:
            return self._generate_pdf_weasyprint(html_content, output_path)
        elif REPORTLAB_AVAILABLE:
            return self._generate_pdf_reportlab(data, invoice_number, output_path)
        else:
            print("❌ Нет доступных библиотек для генерации PDF!")
            print("Установите одну из библиотек:")
            print("  pip install weasyprint")
            print("  pip install reportlab")
            return False

    def _generate_pdf_weasyprint(self, html_content: str, output_path: Path) -> bool:
        """Генерирует PDF с помощью WeasyPrint"""
        try:
            import weasyprint
            
            # Создаем HTML документ
            html_doc = weasyprint.HTML(string=html_content)
            
            # Генерируем PDF
            html_doc.write_pdf(str(output_path))
            
            print(f"✓ PDF успешно создан с WeasyPrint: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при генерации PDF с WeasyPrint: {e}")
            return False

    def _generate_pdf_reportlab(self, data: pd.DataFrame, invoice_number: str, output_path: Path) -> bool:
        """Генерирует PDF с помощью ReportLab"""
        try:
            # Регистрируем шрифт для поддержки кириллицы
            try:
                from reportlab.pdfbase.ttfonts import TTFont
                import platform
                
                system = platform.system()
                if system == "Windows":
                    font_paths = [
                        "C:/Windows/Fonts/arial.ttf",
                        "C:/Windows/Fonts/calibri.ttf", 
                        "C:/Windows/Fonts/tahoma.ttf"
                    ]
                elif system == "Darwin":  # macOS
                    font_paths = [
                        "/System/Library/Fonts/Arial.ttf",
                        "/System/Library/Fonts/Helvetica.ttc"
                    ]
                else:  # Linux
                    font_paths = [
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
                    ]
                
                font_registered = False
                for font_path in font_paths:
                    try:
                        if Path(font_path).exists():
                            pdfmetrics.registerFont(TTFont('CyrillicFont', font_path))
                            font_registered = True
                            print(f"✓ Зарегистрирован шрифт: {font_path}")
                            break
                    except Exception:
                        continue
                
                if not font_registered:
                    print("⚠ Не удалось зарегистрировать системный шрифт, используем стандартный")
                    
            except Exception as e:
                print(f"⚠ Ошибка при регистрации шрифта: {e}")
            
            # Создаем PDF документ
            doc = SimpleDocTemplate(str(output_path), pagesize=A4)
            story = []
            
            # Определяем шрифт для использования
            font_name = 'CyrillicFont' if 'CyrillicFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
            
            # Стили
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=20,
                spaceAfter=30,
                alignment=1,
                fontName=font_name
            )
            
            # Заголовок
            story.append(Paragraph("СЧЕТ НА ОПЛАТУ", title_style))
            story.append(Paragraph(f"№ {invoice_number}", title_style))
            story.append(Spacer(1, 20))
            
            # Информация о счете
            if not data.empty:
                first_row = data.iloc[0]
                
                info_data = [
                    ['Дата:', str(first_row.get('дата', 'Не указана'))],
                    ['Клиент:', str(first_row.get('клиент', 'Не указан'))],
                    ['Статус:', str(first_row.get('статус', 'Ожидает оплаты'))]
                ]
                
                info_table = Table(info_data, colWidths=[3*cm, 8*cm])
                info_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                
                story.append(info_table)
                story.append(Spacer(1, 20))
                
                # Таблица товаров
                table_data = [['№', 'Товар', 'Кол-во', 'Цена', 'Сумма']]
                
                total_sum = 0
                for i, (_, row) in enumerate(data.iterrows(), 1):
                    table_data.append([
                        str(i),
                        str(row.get('товар', '')),
                        str(row.get('количество', '')),
                        f"{row.get('цена_за_единицу', 0):,.2f}",
                        f"{row.get('общая_сумма', 0):,.2f}"
                    ])
                    
                    try:
                        total_sum += float(row.get('общая_сумма', 0))
                    except (ValueError, TypeError):
                        pass
                
                # Создаем таблицу
                items_table = Table(table_data, colWidths=[1*cm, 6*cm, 1.5*cm, 2*cm, 2*cm])
                items_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), font_name),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(items_table)
                story.append(Spacer(1, 20))
                
                # Общая сумма
                story.append(Paragraph(f"Общая сумма: {total_sum:,.2f} руб.", 
                                      ParagraphStyle('Total', fontSize=14, alignment=2, fontName=font_name)))
            
            # Строим PDF
            doc.build(story)
            
            print(f"✓ PDF успешно создан с ReportLab: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при генерации PDF с ReportLab: {e}")
            return False

    def open_pdf(self, pdf_path: Path) -> None:
        """Автоматически открывает PDF в системной программе"""
        try:
            system = platform.system()
            
            if system == "Windows":
                os.startfile(str(pdf_path))
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(pdf_path)])
            elif system == "Linux":
                subprocess.run(["xdg-open", str(pdf_path)])
            else:
                print(f"⚠ Неизвестная операционная система: {system}")
                print(f"PDF сохранен в: {pdf_path}")
                
        except Exception as e:
            print(f"⚠ Не удалось открыть PDF: {e}")
            print(f"PDF сохранен в: {pdf_path}")

    def display_menu(self, items: List[Path], title: str) -> Optional[Path]:
        """Отображает меню выбора и возвращает выбранный элемент"""
        if not items:
            print(f"❌ {title} не найдены!")
            return None
        
        print(f"\n📋 {title}:")
        print("-" * 50)
        
        for i, item in enumerate(items, 1):
            print(f"{i}. {item.name}")
        
        print("-" * 50)
        
        while True:
            try:
                choice = input(f"Выберите номер (1-{len(items)}): ").strip()
                choice_num = int(choice)
                
                if 1 <= choice_num <= len(items):
                    return items[choice_num - 1]
                else:
                    print(f"❌ Пожалуйста, введите число от 1 до {len(items)}")
                    
            except ValueError:
                print("❌ Пожалуйста, введите корректное число")
            except KeyboardInterrupt:
                print("\n👋 Программа завершена пользователем")
                sys.exit(0)

    def display_invoice_menu(self, invoices: List[str]) -> Optional[str]:
        """Отображает меню выбора номера счета"""
        if not invoices:
            print("❌ Доступные счета не найдены!")
            return None
        
        print(f"\n📄 Доступные счета:")
        print("-" * 50)
        
        for i, invoice in enumerate(invoices, 1):
            print(f"{i}. {invoice}")
        
        print("-" * 50)
        
        while True:
            try:
                choice = input(f"Выберите номер счета (1-{len(invoices)}): ").strip()
                choice_num = int(choice)
                
                if 1 <= choice_num <= len(invoices):
                    return invoices[choice_num - 1]
                else:
                    print(f"❌ Пожалуйста, введите число от 1 до {len(invoices)}")
                    
            except ValueError:
                print("❌ Пожалуйста, введите корректное число")
            except KeyboardInterrupt:
                print("\n👋 Программа завершена пользователем")
                sys.exit(0)

    def run(self):
        """Основной метод запуска программы"""
        print("🚀 Генератор счетов в PDF")
        print("=" * 50)
        
        # Получаем доступные файлы
        data_files = self.get_data_files()
        template_files = self.get_template_files()
        
        # Выводим информацию о доступных файлах
        print(f"\n📁 Найдено файлов данных: {len(data_files)}")
        for file in data_files:
            print(f"   • {file.name}")
        
        print(f"\n📄 Найдено HTML шаблонов: {len(template_files)}")
        for file in template_files:
            print(f"   • {file.name}")
        
        if not data_files:
            print("\n❌ Не найдено файлов данных в директории 'data'!")
            print("   Добавьте CSV или JSON файлы в директорию 'data' и запустите программу снова.")
            return
        
        if not template_files:
            print("\n❌ Не найдено HTML шаблонов в директории 'templates'!")
            print("   Добавьте HTML шаблоны в директорию 'templates' и запустите программу снова.")
            return
        
        # Выбор файла данных
        selected_data_file = self.display_menu(data_files, "Файлы данных")
        if not selected_data_file:
            return
        
        # Выбор шаблона
        selected_template = self.display_menu(template_files, "HTML шаблоны")
        if not selected_template:
            return
        
        # Чтение данных
        print(f"\n📖 Читаем данные из: {selected_data_file.name}")
        
        if selected_data_file.suffix.lower() == '.csv':
            data = self.read_csv_file(selected_data_file)
        elif selected_data_file.suffix.lower() == '.json':
            # Для JSON используем старый метод
            with open(selected_data_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            data = pd.DataFrame(json_data)
        else:
            print("❌ Неподдерживаемый формат файла!")
            return
        
        if data is None or data.empty:
            print("❌ Файл данных пуст или не удалось прочитать!")
            return
        
        # Получение доступных счетов
        invoices = self.get_available_invoices(data)
        
        # Выбор счета
        selected_invoice = self.display_invoice_menu(invoices)
        if not selected_invoice:
            return
        
        # Фильтрация данных по выбранному счету
        filtered_data = self.filter_data_by_invoice(data, selected_invoice)
        
        if filtered_data.empty:
            print("❌ Данные для выбранного счета не найдены!")
            return
        
        # Рендеринг шаблона
        print(f"\n🎨 Рендерим шаблон: {selected_template.name}")
        html_content = self.render_template(selected_template, filtered_data, selected_invoice)
        
        if not html_content:
            print("❌ Не удалось сгенерировать HTML контент!")
            return
        
        # Генерация PDF
        output_filename = f"schet_{selected_invoice}_{selected_template.stem}.pdf"
        output_path = self.output_dir / output_filename
        
        print(f"\n📄 Генерируем PDF: {output_filename}")
        
        if self.generate_pdf(html_content, output_path, filtered_data, selected_invoice):
            print(f"\n✅ PDF успешно создан!")
            print(f"📁 Путь: {output_path.absolute()}")
            
            # Автоматическое открытие PDF
            print("\n🔍 Открываем PDF...")
            self.open_pdf(output_path)
        else:
            print("\n❌ Ошибка при создании PDF!")

    def generate_new_invoice(self, customer_name: str, items: List[Dict[str, Any]]) -> str:
        """Генерирует новый счет с автоматическим номером"""
        # Получаем следующий номер счета
        invoice_number = self.get_next_invoice_number()
        
        # Создаем данные для нового счета
        invoice_data = []
        for i, item in enumerate(items):
            invoice_data.append({
                'номер_счета': invoice_number,
                'дата': datetime.now().strftime('%Y-%m-%d'),
                'клиент': customer_name,
                'товар': item.get('товар', ''),
                'количество': item.get('количество', 1),
                'цена_за_единицу': item.get('цена_за_единицу', 0),
                'общая_сумма': item.get('количество', 1) * item.get('цена_за_единицу', 0),
                'статус': 'Ожидает оплаты'
            })
        
        # Создаем DataFrame
        data = pd.DataFrame(invoice_data)
        
        # Получаем шаблон
        template_files = self.get_template_files()
        if not template_files:
            print("❌ Не найдены HTML шаблоны!")
            return None
        
        # Используем первый доступный шаблон
        template = template_files[0]
        
        # Рендерим шаблон
        html_content = self.render_template(template, data, invoice_number)
        
        if not html_content:
            print("❌ Не удалось сгенерировать HTML контент!")
            return None
        
        # Генерируем PDF
        output_filename = f"novyi_schet_{invoice_number}.pdf"
        output_path = self.output_dir / output_filename
        
        print(f"\n📄 Генерируем новый счет: {output_filename}")
        
        if self.generate_pdf(html_content, output_path, data, invoice_number):
            print(f"\n✅ Новый счет успешно создан!")
            print(f"📁 Путь: {output_path.absolute()}")
            print(f"📋 Номер счета: {invoice_number}")
            
            # Автоматическое открытие PDF
            print("\n🔍 Открываем PDF...")
            self.open_pdf(output_path)
            
            return invoice_number
        else:
            print("\n❌ Ошибка при создании нового счета!")
            return None


def main():
    """Точка входа в программу"""
    try:
        generator = SchetGenerator()
        generator.run()
    except KeyboardInterrupt:
        print("\n👋 Программа завершена пользователем")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
