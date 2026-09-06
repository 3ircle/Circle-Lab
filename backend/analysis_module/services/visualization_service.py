import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
import pandas as pd


class VisualizationService:
    @staticmethod
    def generate_seaborn_chart(df: pd.DataFrame, col_name: str, data_type: str) -> io.BytesIO:
        """
        تولید نمودار با Seaborn با استایل Dark Mode کاستوم متناسب با CircleLab
        """
        fig, ax = plt.subplots(figsize=(6, 3.2), dpi=100)

        # Dark Theme Colors
        fig.patch.set_facecolor('#1E293B')
        ax.set_facecolor('#1E293B')
        ax.tick_params(colors='#CBD5E1', labelsize=8)
        ax.xaxis.label.set_color('#CBD5E1')
        ax.yaxis.label.set_color('#CBD5E1')
        ax.title.set_color('#FFFFFF')
        for spine in ax.spines.values():
            spine.set_color('#334155')

        ax.grid(True, linestyle='--', alpha=0.2, color='#CBD5E1')

        series = df[col_name].dropna()

        if data_type in ["عدد صحیح (Integer)", "عدد اعشاری (Float)"]:
            numeric_series = pd.to_numeric(series, errors='coerce').dropna()
            if not numeric_series.empty:
                sns.histplot(numeric_series, kde=True, ax=ax, color='#22D3EE', edgecolor='#0F172A', alpha=0.7)
                ax.set_ylabel('فراوانی', fontname='DejaVu Sans', fontsize=9)
        else:
            counts = series.astype(str).value_counts().head(8)
            if not counts.empty:
                palette = ['#6366F1', '#22D3EE', '#A855F7', '#34D399', '#F59E0B', '#EF4444', '#818CF8', '#C084FC']
                sns.barplot(x=counts.index, y=counts.values, ax=ax, palette=palette[:len(counts)], hue=counts.index, legend=False)
                ax.set_ylabel('تعداد', fontname='DejaVu Sans', fontsize=9)
                plt.xticks(rotation=25, ha='right')

        ax.set_xlabel(col_name, fontsize=9)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        return buf

    @staticmethod
    def generate_missing_values_chart(df: pd.DataFrame) -> io.BytesIO:
        """
        تولید نمودار ماتریس مقادیر مفقوده (MSNO Matrix / Missing Values Matrix)
        با پشتیبانی از تعداد بالای ستون‌ها و استایل Dark Mode کاستوم CircleLab
        """
        num_cols = len(df.columns)
        if num_cols == 0:
            return None

        # محاسبه عرض پویا بر اساس تعداد ستون‌ها تا اسکوئیش و ناخوانا نشوند
        fig_width = max(10.0, num_cols * 0.38)
        fig, ax = plt.subplots(figsize=(fig_width, 4.2), dpi=100)

        # Dark Theme Colors
        fig.patch.set_facecolor('#1E293B')
        ax.set_facecolor('#1E293B')

        try:
            import missingno as msno
            msno.matrix(
                df,
                sparkline=False,
                color=(0.133, 0.827, 0.933),
                fontsize=9,
                labels=True,
                ax=ax
            )
            ax.set_facecolor('#1E293B')
            ax.tick_params(colors='#CBD5E1', labelsize=8)
        except Exception:
            # Fallback به Matplotlib / Seaborn
            if len(df) > 300:
                df_sampled = df.iloc[::len(df)//300]
            else:
                df_sampled = df

            not_null_matrix = df_sampled.notnull().values
            cmap = mcolors.ListedColormap(['#334155', '#22D3EE'])

            ax.imshow(not_null_matrix, aspect='auto', cmap=cmap, interpolation='none')

            ax.set_xticks(range(num_cols))
            ax.set_xticklabels(df.columns, rotation=45, ha='right', colors='#CBD5E1', fontsize=8)
            ax.set_yticks([])
            ax.tick_params(colors='#CBD5E1')

            for spine in ax.spines.values():
                spine.set_color('#334155')

        ax.set_title('ماتریس مقادیر مفقوده (Missing Values Matrix)', color='#FFFFFF', fontsize=11, pad=12)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        return buf
