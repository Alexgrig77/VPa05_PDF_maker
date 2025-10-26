#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Generator - Генератор PDF документов из CSV/JSON файлов
Использует HTML-шаблоны и библиотеку WeasyPrint
"""

import os
import json
import pandas as pd
from pathlib import Path
import platform
import subprocess
import sys
from typing import List, Dict, Any, Optional

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


class PDFGenerator:
    def __init__(self):
        self.data_dir = Path("data")
        self.templates_dir = Path("templates")
        self.output_dir = Path("output")
        
        # Создаем директории если их нет
        self.data_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        
        # Поддержка кириллицы
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
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #333;
            padding-bottom: 20px;
        }
        
        .invoice-info {
            margin-bottom: 20px;
        }
        
        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        
        .items-table th,
        .items-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        .items-table th {
            background-color: #f5f5f5;
            font-weight: bold;
        }
        
        .total {
            text-align: right;
            font-weight: bold;
            font-size: 14px;
            margin-top: 20px;
        }
        """

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

    def read_json_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Читает JSON файл"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Если это не список, оборачиваем в список
            if not isinstance(data, list):
                data = [data]
            
            print("✓ JSON файл успешно прочитан")
            return data
            
        except Exception as e:
            print(f"❌ Ошибка при чтении JSON файла: {e}")
            return []

    def get_available_invoices(self, data: Any) -> List[str]:
        """Получает список доступных invoice_id из данных"""
        invoices = set()
        
        if isinstance(data, pd.DataFrame):
            # Для DataFrame ищем колонку с invoice_id
            invoice_columns = [col for col in data.columns if 'invoice' in col.lower() or 'id' in col.lower()]
            if invoice_columns:
                invoices.update(data[invoice_columns[0]].astype(str).unique())
        elif isinstance(data, list):
            # Для списка словарей ищем поле invoice_id
            for item in data:
                if isinstance(item, dict):
                    for key in item.keys():
                        if 'invoice' in key.lower() or 'id' in key.lower():
                            invoices.add(str(item[key]))
                            break
        
        return sorted(list(invoices))

    def filter_data_by_invoice(self, data: Any, invoice_id: str) -> Any:
        """Фильтрует данные по invoice_id"""
        if isinstance(data, pd.DataFrame):
            # Для DataFrame ищем колонку с invoice_id
            invoice_columns = [col for col in data.columns if 'invoice' in col.lower() or 'id' in col.lower()]
            if invoice_columns:
                filtered = data[data[invoice_columns[0]].astype(str) == invoice_id]
                return filtered
        elif isinstance(data, list):
            # Для списка словарей фильтруем по invoice_id
            filtered = []
            for item in data:
                if isinstance(item, dict):
                    for key in item.keys():
                        if 'invoice' in key.lower() or 'id' in key.lower():
                            if str(item[key]) == invoice_id:
                                filtered.append(item)
                            break
            
            return filtered
        
        return data

    def render_template(self, template_path: Path, data: Any, invoice_id: str) -> str:
        """Рендерит HTML шаблон с данными"""
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # Простая замена плейсхолдеров
            html_content = template_content
            
            # Заменяем общие плейсхолдеры
            html_content = html_content.replace('{{invoice_id}}', str(invoice_id))
            html_content = html_content.replace('{{css_styles}}', self.css_styles)
            
            # Если данные - это DataFrame
            if isinstance(data, pd.DataFrame):
                if not data.empty:
                    # Создаем таблицу из DataFrame
                    table_html = data.to_html(index=False, classes='items-table', escape=False)
                    html_content = html_content.replace('{{data_table}}', table_html)
                    
                    # Добавляем общую информацию
                    for col in data.columns:
                        placeholder = f'{{{{{col}}}}}'
                        if placeholder in html_content and len(data) > 0:
                            html_content = html_content.replace(placeholder, str(data.iloc[0][col]))
            
            # Если данные - это список словарей
            elif isinstance(data, list) and data:
                # Создаем таблицу из списка словарей
                if data:
                    df = pd.DataFrame(data)
                    table_html = df.to_html(index=False, classes='items-table', escape=False)
                    html_content = html_content.replace('{{data_table}}', table_html)
                    
                    # Добавляем информацию из первого элемента
                    for key, value in data[0].items():
                        placeholder = f'{{{{{key}}}}}'
                        html_content = html_content.replace(placeholder, str(value))
            
            return html_content
            
        except Exception as e:
            print(f"❌ Ошибка при рендеринге шаблона: {e}")
            return ""

    def generate_pdf(self, html_content: str, output_path: Path, data: Any, invoice_id: str) -> bool:
        """Генерирует PDF из HTML контента или данных"""
        if WEASYPRINT_AVAILABLE:
            return self._generate_pdf_weasyprint(html_content, output_path)
        elif REPORTLAB_AVAILABLE:
            return self._generate_pdf_reportlab(data, invoice_id, output_path)
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

    def _generate_pdf_reportlab(self, data: Any, invoice_id: str, output_path: Path) -> bool:
        """Генерирует PDF с помощью ReportLab"""
        try:
            # Регистрируем шрифт для поддержки кириллицы
            try:
                # Пытаемся зарегистрировать системный шрифт
                from reportlab.pdfbase.ttfonts import TTFont
                import platform
                
                system = platform.system()
                if system == "Windows":
                    # Windows шрифты
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
            
            # Стили с поддержкой кириллицы
            styles = getSampleStyleSheet()
            
            # Определяем шрифт для использования
            font_name = 'CyrillicFont' if 'CyrillicFont' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'
            
            # Создаем стили с правильным шрифтом
            normal_style = ParagraphStyle(
                'Normal',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=10
            )
            
            bold_style = ParagraphStyle(
                'Bold',
                parent=styles['Normal'],
                fontName=font_name,
                fontSize=10,
                fontWeight='bold'
            )
            
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1,  # Центрирование
                fontName=font_name
            )
            
            # Заголовок
            story.append(Paragraph("СЧЕТ НА ОПЛАТУ", title_style))
            story.append(Paragraph(f"№ {invoice_id}", title_style))
            story.append(Spacer(1, 20))
            
            # Информация о счете
            if isinstance(data, pd.DataFrame) and not data.empty:
                # Для DataFrame
                first_row = data.iloc[0]
                
                info_data = [
                    ['Дата:', str(first_row.get('date', 'Не указана'))],
                    ['Клиент:', str(first_row.get('customer_name', 'Не указан'))],
                    ['Email:', str(first_row.get('customer_email', 'Не указан'))]
                ]
                
                info_table = Table(info_data, colWidths=[3*cm, 8*cm])
                info_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), font_name),  # Используем шрифт для всех ячеек
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                
                story.append(info_table)
                story.append(Spacer(1, 20))
                
                # Таблица товаров
                if len(data) > 0:
                    # Подготавливаем данные для таблицы
                    table_data = [['Товар', 'Количество', 'Цена', 'Сумма']]
                    
                    total_sum = 0
                    for _, row in data.iterrows():
                        item_name = str(row.get('item_name', ''))
                        quantity = str(row.get('quantity', ''))
                        price = str(row.get('price', ''))
                        total = str(row.get('total', ''))
                        
                        table_data.append([item_name, quantity, price, total])
                        
                        try:
                            total_sum += float(row.get('total', 0))
                        except (ValueError, TypeError):
                            pass
                    
                    # Создаем таблицу
                    items_table = Table(table_data, colWidths=[6*cm, 2*cm, 2*cm, 2*cm])
                    items_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, -1), font_name),  # Используем шрифт для всех ячеек
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    
                    story.append(items_table)
                    story.append(Spacer(1, 20))
                    
                    # Общая сумма
                    story.append(Paragraph(f"Общая сумма: {total_sum:.2f} руб.", 
                                          ParagraphStyle('Total', fontSize=12, alignment=2, fontName=font_name)))
                
            elif isinstance(data, list) and data:
                # Для списка словарей
                first_item = data[0]
                
                info_data = [
                    ['Дата:', str(first_item.get('date', 'Не указана'))],
                    ['Клиент:', str(first_item.get('customer', {}).get('name', 'Не указан'))],
                    ['Email:', str(first_item.get('customer', {}).get('email', 'Не указан'))]
                ]
                
                info_table = Table(info_data, colWidths=[3*cm, 8*cm])
                info_table.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, -1), font_name),  # Используем шрифт для всех ячеек
                    ('FONTSIZE', (0, 0), (-1, -1), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ]))
                
                story.append(info_table)
                story.append(Spacer(1, 20))
                
                # Таблица товаров
                if 'items' in first_item and isinstance(first_item['items'], list):
                    table_data = [['Товар', 'Описание', 'Количество', 'Цена', 'Сумма']]
                    
                    for item in first_item['items']:
                        table_data.append([
                            str(item.get('name', '')),
                            str(item.get('description', '')),
                            str(item.get('quantity', '')),
                            str(item.get('price', '')),
                            str(item.get('total', ''))
                        ])
                    
                    items_table = Table(table_data, colWidths=[3*cm, 4*cm, 1.5*cm, 1.5*cm, 1.5*cm])
                    items_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, -1), font_name),  # Используем шрифт для всех ячеек
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    
                    story.append(items_table)
                    story.append(Spacer(1, 20))
                    
                    # Общая сумма
                    total = first_item.get('total', 0)
                    story.append(Paragraph(f"Общая сумма: {total} руб.", 
                                          ParagraphStyle('Total', fontSize=12, alignment=2, fontName=font_name)))
            
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
        """Отображает меню выбора invoice_id"""
        if not invoices:
            print("❌ Доступные счета не найдены!")
            return None
        
        print(f"\n📄 Доступные счета (invoice_id):")
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
        print("🚀 PDF Generator - Генератор PDF документов")
        print("=" * 60)
        
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
            data = self.read_json_file(selected_data_file)
        else:
            print("❌ Неподдерживаемый формат файла!")
            return
        
        if data is None or (isinstance(data, (list, pd.DataFrame)) and len(data) == 0):
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
        
        if isinstance(filtered_data, (list, pd.DataFrame)) and len(filtered_data) == 0:
            print("❌ Данные для выбранного счета не найдены!")
            return
        
        # Рендеринг шаблона
        print(f"\n🎨 Рендерим шаблон: {selected_template.name}")
        html_content = self.render_template(selected_template, filtered_data, selected_invoice)
        
        if not html_content:
            print("❌ Не удалось сгенерировать HTML контент!")
            return
        
        # Генерация PDF
        output_filename = f"invoice_{selected_invoice}_{selected_template.stem}.pdf"
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


def main():
    """Точка входа в программу"""
    try:
        generator = PDFGenerator()
        generator.run()
    except KeyboardInterrupt:
        print("\n👋 Программа завершена пользователем")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
